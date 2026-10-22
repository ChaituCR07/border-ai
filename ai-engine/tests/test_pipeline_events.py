import json
import threading

import pytest

from app.analytics.engine import RuleEngine
from app.behaviour.engine import BehaviourEngine
from app.events.journal import publish_journal
from app.events.processor import EventProcessor, MemorySink
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


def run_pipeline(tmp_path, sample_video, zones_dir, publisher):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonWalker(), mgr, TrackerParams(), RuleEngine(zones_dir), tmp_path / "runs",
                 behaviour=BehaviourEngine(make_behaviour_cfg(behaviour_rules())),
                 scorer=ThreatScorer(make_scoring()), clock_start=epoch("2026-10-12 02:13:00"),
                 publisher=publisher)
    p.start()
    return p


def journal_ids(p):
    return [json.loads(l)["event_id"] for l in (p.run_dir / "events.jsonl").read_text().splitlines()]


@pytest.mark.integration
def test_every_journaled_event_reaches_the_bus_and_the_processor(tmp_path, sample_video, zones_dir):
    client, cfg = InMemoryStreamClient(), make_events_cfg()
    p = run_pipeline(tmp_path, sample_video, zones_dir, EventPublisher(StreamTransport(client, cfg), cfg))
    assert p.join(timeout=60)

    journal = journal_ids(p)
    assert journal and "THREAT_ALERT" in (p.run_dir / "events.jsonl").read_text()
    on_stream = [f["event_id"] for _, f in client.range(cfg.stream, 10000)]
    assert on_stream == journal                                                  # same events, same order
    assert client.range(cfg.stream, 1)[0][1]["run_id"] == p.run_id
    assert len(client.range(cfg.alerts_stream, 100)) == 3                        # LOW, MEDIUM, HIGH alerts
    assert p.status()["events_bus"]["published"] == len(journal)

    proc = EventProcessor(client, [MemorySink()], cfg)
    drain(proc)
    assert proc.sinks[0].ids == journal


@pytest.mark.integration
def test_an_outage_during_the_run_loses_nothing(tmp_path, sample_video, zones_dir):
    client, cfg = InMemoryStreamClient(), make_events_cfg(shutdown_timeout_s=10.0)
    client.down = True
    threading.Timer(0.4, lambda: setattr(client, "down", False)).start()        # the bus comes back while the run is going
    p = run_pipeline(tmp_path, sample_video, zones_dir, EventPublisher(StreamTransport(client, cfg), cfg))
    assert p.join(timeout=60)

    assert [f["event_id"] for _, f in client.range(cfg.stream, 10000)] == journal_ids(p)
    assert p.status()["events_bus"]["retries"] >= 1


@pytest.mark.integration
def test_a_bus_that_stays_down_never_breaks_the_pipeline_and_the_journal_can_be_replayed(tmp_path, sample_video, zones_dir):
    client, cfg = InMemoryStreamClient(), make_events_cfg(shutdown_timeout_s=0.3)
    client.down = True
    p = run_pipeline(tmp_path, sample_video, zones_dir, EventPublisher(StreamTransport(client, cfg), cfg))
    assert p.join(timeout=60)

    st = p.status()
    assert st["state"] == "finished" and st["events_bus"]["connected"] is False
    assert st["events_bus"]["dropped_on_shutdown"] > 0
    journal = journal_ids(p)
    assert journal                                                                # the journal has everything

    client.down = False                                                           # later, the bus is back
    n = publish_journal(p.run_dir / "events.jsonl", StreamTransport(client, cfg), run_id=p.run_id)
    assert n == len(journal)
    proc = EventProcessor(client, [MemorySink()], cfg)
    drain(proc, rounds=100)
    assert sorted(proc.sinks[0].ids) == sorted(journal)


@pytest.mark.integration
def test_the_pipeline_works_without_a_publisher(tmp_path, sample_video, zones_dir):
    p = run_pipeline(tmp_path, sample_video, zones_dir, None)
    assert p.join(timeout=60) and p.status()["events_bus"] is None
