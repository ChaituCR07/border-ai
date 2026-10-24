import threading
import time

import pytest

from app.db.events_repo import InMemoryEventRepository
from app.events.db_sink import PostgresEventSink
from app.events.envelope import envelope_from_event
from app.events.processor import EventProcessor, PermanentSinkError
from app.events.streams import InMemoryStreamClient
from db_helpers import alert_event, plate_event, summary_event, zone_event
from events_helpers import drain, make_events_cfg


def env(event):
    return envelope_from_event(event, "RUN1")


def test_every_kind_of_event_is_stored_with_its_derived_rows():
    repo = InMemoryEventRepository()
    sink = PostgresEventSink(repo)
    for e in (zone_event(1), alert_event(2, alert_id="A1"), plate_event(3), summary_event(4)):
        sink.handle(env(e))
    assert repo.count_events() == 4 and len(repo.list_alerts()) == 1
    assert len(repo.list_vehicles()) == 1 and len(repo.list_detections()) == 1
    assert sink.stats["stored"] == 4 and sink.stats["alerts"] == 1 and sink.stats["cameras_registered"] == 1


def test_a_repeated_event_is_counted_as_a_duplicate_and_changes_nothing():
    repo = InMemoryEventRepository()
    sink = PostgresEventSink(repo)
    e = env(alert_event(1, alert_id="A1"))
    sink.handle(e)
    sink.handle(e)
    assert repo.count_events() == 1 and sink.stats["duplicates"] == 1 and len(repo.list_alerts()) == 1


def test_data_that_can_never_be_stored_is_a_permanent_error():
    sink = PostgresEventSink(InMemoryEventRepository())
    bad_alert = alert_event(1)
    bad_alert.details.pop("alert_id")
    with pytest.raises(PermanentSinkError, match="mapping"):
        sink.handle(env(bad_alert))
    with pytest.raises(PermanentSinkError, match="invalid_record"):
        sink.handle(env(zone_event(1, cam="bad camera!")))


def test_a_database_outage_is_a_retryable_error_not_a_permanent_one():
    from app.watchlist.models import RepoUnavailable
    repo = InMemoryEventRepository()
    repo.fail = True
    with pytest.raises(RepoUnavailable):
        PostgresEventSink(repo).handle(env(zone_event(1)))


def processor_with_db(repo=None):
    client = InMemoryStreamClient()
    cfg = make_events_cfg()
    repo = repo or InMemoryEventRepository()
    return EventProcessor(client, [PostgresEventSink(repo)], cfg), client, cfg, repo


def test_the_processor_stores_events_and_dead_letters_the_bad_ones():
    proc, client, cfg, repo = processor_with_db()
    good = [zone_event(1), alert_event(2, alert_id="A1"), plate_event(3)]
    bad = alert_event(4)
    bad.details.pop("alert_id")
    for e in good + [bad]:
        client.xadd(cfg.stream, env(e).to_fields())
    drain(proc)
    assert repo.count_events() == 3 and proc.status()["dead_lettered"] == 1
    dead = client.range(cfg.dead_stream, 10)
    assert "mapping" in dead[0][1]["dead_reason"] and client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_a_database_outage_leaves_messages_pending_and_recovery_stores_everything_once():
    proc, client, cfg, repo = processor_with_db()
    events = [zone_event(i) for i in range(5)]
    for e in events:
        client.xadd(cfg.stream, env(e).to_fields())
    repo.fail = True
    proc.run_once()
    assert repo.fail and client.pending_count(cfg.stream, cfg.processor.group) == 5 and client.length(cfg.dead_stream) == 0
    repo.fail = False
    time.sleep(0.12)                                                  # longer than reclaim_idle_ms
    drain(proc)
    assert repo.count_events() == 5 and client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_duplicates_from_the_bus_never_create_duplicate_rows():
    proc, client, cfg, repo = processor_with_db()
    e = alert_event(1, alert_id="A1")
    for _ in range(4):
        client.xadd(cfg.stream, env(e).to_fields())
    drain(proc)
    assert repo.count_events() == 1 and len(repo.list_alerts()) == 1


def test_two_processors_sharing_the_group_fill_one_database_without_overlap():
    client, cfg, repo = InMemoryStreamClient(), make_events_cfg(), InMemoryEventRepository()
    procs = [EventProcessor(client, [PostgresEventSink(repo)], cfg, consumer=f"c{i}") for i in range(2)]
    events = [zone_event(i) for i in range(30)]
    for e in events:
        client.xadd(cfg.stream, env(e).to_fields())
    for _ in range(6):
        for p in procs:
            p.pc.batch = 4
            p.run_once()
    assert repo.count_events() == 30
