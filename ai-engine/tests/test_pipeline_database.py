import json

import pytest

from app.analytics.engine import RuleEngine
from app.behaviour.engine import BehaviourEngine
from app.db.events_repo import InMemoryEventRepository, PostgresEventRepository
from app.events.db_sink import PostgresEventSink
from app.events.processor import EventProcessor
from app.events.publisher import EventPublisher, StreamTransport
from app.events.streams import InMemoryStreamClient
from app.pipeline.pipeline import Pipeline
from app.threat.scorer import ThreatScorer
from app.tracking.tracker import TrackerParams
from behaviour_helpers import epoch, make_cfg as make_behaviour_cfg
from events_helpers import drain, make_events_cfg
from ingestion.camera_manager import CameraManager
from ingestion.sources.file_source import FileSource
from test_pipeline_threat import FakePersonWalker, behaviour_rules, sample_video, zones_dir   # noqa: F401
from threat_helpers import make_scoring


def run_into(repo, tmp_path, sample_video, zones_dir):
    client, cfg = InMemoryStreamClient(), make_events_cfg()
    publisher = EventPublisher(StreamTransport(client, cfg), cfg)
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonWalker(), mgr, TrackerParams(), RuleEngine(zones_dir), tmp_path / "runs",
                 behaviour=BehaviourEngine(make_behaviour_cfg(behaviour_rules())),
                 scorer=ThreatScorer(make_scoring()), clock_start=epoch("2026-10-12 02:13:00"),
                 publisher=publisher, track_summary_min_hits=5)
    p.start()
    assert p.join(timeout=60)
    sink = PostgresEventSink(repo)
    proc = EventProcessor(client, [sink], cfg)
    drain(proc, rounds=200)
    journal = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    return p, journal, proc, sink


def check(repo, p, journal, proc):
    assert journal
    assert repo.count_events() == len(journal)                                    # every journaled event is in the database, once
    by_type = {}
    for e in journal:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    for etype, n in by_type.items():
        assert repo.count_events(event_type=etype) == n
    assert proc.status().get("dead_lettered", 0) == 0

    alerts = sorted(repo.list_alerts(), key=lambda a: a["created_at"])
    assert [(a["priority"], a["threat_score"]) for a in alerts] == [("LOW", 10), ("MEDIUM", 30), ("HIGH", 60)]   # Scenario 1
    assert all(a["status"] == "NEW" and a["camera_id"] == "CAM_T" for a in alerts)
    assert repo.alert_counts()["HIGH"]["new"] == 1 and repo.alert_counts()["CRITICAL"]["total"] == 0

    detections = repo.list_detections(camera_id="CAM_T")
    assert len(detections) == by_type.get("TRACK_SUMMARY", 0) >= 1               # one summary per tracked object
    assert detections[0]["object_type"] == "person" and detections[0]["hits"] >= 5

    camera = repo.get_camera("CAM_T")
    assert camera["status"] == "UNREGISTERED"                                     # nobody seeded it: visible, not lost


@pytest.mark.integration
def test_the_pipeline_fills_the_database_from_the_bus(tmp_path, sample_video, zones_dir):
    repo = InMemoryEventRepository()
    p, journal, proc, _ = run_into(repo, tmp_path, sample_video, zones_dir)
    check(repo, p, journal, proc)


@pytest.mark.integration
@pytest.mark.db
def test_the_pipeline_fills_the_real_database_from_the_bus(tmp_path, sample_video, zones_dir, pg_dsn):
    repo = PostgresEventRepository(pg_dsn)
    with repo._conn() as conn:
        conn.execute("TRUNCATE alert_history, alerts, vehicles, detections, events, cameras RESTART IDENTITY CASCADE")
    p, journal, proc, _ = run_into(repo, tmp_path, sample_video, zones_dir)
    check(repo, p, journal, proc)
    first = repo.list_events(limit=1)[0]
    assert first["event_ref"].startswith("EVT_") and first["run_id"] == p.run_id
    repo.close()


@pytest.mark.integration
def test_replaying_the_same_run_twice_adds_nothing(tmp_path, sample_video, zones_dir):
    from app.events.journal import publish_journal
    repo = InMemoryEventRepository()
    p, journal, proc, sink = run_into(repo, tmp_path, sample_video, zones_dir)
    before = repo.stats()
    client, cfg = InMemoryStreamClient(), make_events_cfg()
    publish_journal(p.run_dir / "events.jsonl", StreamTransport(client, cfg), run_id=p.run_id)
    again = EventProcessor(client, [sink], cfg)
    drain(again, rounds=100)
    assert repo.stats() == before and sink.stats["duplicates"] >= len(journal)
