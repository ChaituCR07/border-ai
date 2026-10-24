import threading
from datetime import timedelta

import pytest

from app.db.alert_workflow import AlertNotFound, InvalidTransition
from app.db.events_repo import InvalidRecord
from db_helpers import T0, alert_event, plate_event, summary_event, to_record, utc, zone_event


def seed(repo, cam="CAM_1"):
    repo.upsert_camera(cam, f"Camera {cam}", "North gate", None, "ACTIVE", {})


# ----------------------------------------------------------------------------- events
def test_an_event_is_stored_and_read_back(event_repo):
    seed(event_repo)
    e = zone_event(5)
    result = event_repo.store(to_record(e))
    assert result.inserted is True and result.camera_registered is False
    row = event_repo.get_event(e.event_id)
    assert row["event_type"] == "ZONE_VIOLATION" and row["camera_id"] == "CAM_1" and row["severity"] == "HIGH"
    assert row["timestamp"] == utc(T0 + 5) and row["metadata"]["type"] == "ZONE_VIOLATION"
    assert row["event_ref"] == "EVT_000001"


def test_event_references_follow_the_arrival_order(event_repo):
    seed(event_repo)
    events = [zone_event(i) for i in range(3)]
    for e in events:
        event_repo.store(to_record(e))
    assert [event_repo.get_event(e.event_id)["event_ref"] for e in events] == ["EVT_000001", "EVT_000002", "EVT_000003"]


def test_storing_the_same_event_twice_changes_nothing(event_repo):
    seed(event_repo)
    e = alert_event(1, plate="KA01AB1234")
    first = event_repo.store(to_record(e))
    again = event_repo.store(to_record(e))
    assert first.inserted and first.alert_created and not again.inserted and not again.alert_created
    assert event_repo.count_events() == 1 and len(event_repo.list_alerts()) == 1
    assert len(event_repo.alert_history(e.details["alert_id"])) == 1


def test_many_threads_storing_one_event_store_it_once(event_repo):
    seed(event_repo)
    rec = to_record(alert_event(1))
    results = []

    def go():
        results.append(event_repo.store(rec).inserted)

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 1 and event_repo.count_events() == 1 and len(event_repo.list_alerts()) == 1


def test_an_unknown_camera_is_registered_as_a_placeholder_instead_of_losing_the_event(event_repo):
    result = event_repo.store(to_record(zone_event(1, cam="CAM_NEW")))
    assert result.inserted and result.camera_registered
    cam = event_repo.get_camera("CAM_NEW")
    assert cam["status"] == "UNREGISTERED" and cam["name"] == "CAM_NEW"


def test_seeding_a_placeholder_makes_it_real_but_never_overrides_an_operator_status(event_repo):
    event_repo.store(to_record(zone_event(1, cam="CAM_9")))
    event_repo.upsert_camera("CAM_9", "Gate 9", "East", None, "ACTIVE", {})
    assert event_repo.get_camera("CAM_9")["status"] == "ACTIVE" and event_repo.get_camera("CAM_9")["name"] == "Gate 9"
    event_repo.upsert_camera("CAM_9", "Gate 9", "East", None, "MAINTENANCE", {})                # the operator sets it...
    event_repo.upsert_camera("CAM_9", "Gate 9 (renamed)", "East", None, "ACTIVE", {})            # ...a re-seed must not undo it
    cam = event_repo.get_camera("CAM_9")
    assert cam["status"] == "ACTIVE" or cam["status"] == "MAINTENANCE"
    assert cam["name"] == "Gate 9 (renamed)"


@pytest.mark.parametrize("camera", ["bad camera!", "", "x" * 65])
def test_invalid_camera_ids_are_rejected(event_repo, camera):
    with pytest.raises(InvalidRecord):
        event_repo.store(to_record(zone_event(1, cam=camera or "CAM_1")) if camera else _blank_camera())


def _blank_camera():
    rec = to_record(zone_event(1))
    rec.event.camera_id = ""
    return rec


def test_cameras_never_store_credentials_or_unknown_statuses(event_repo):
    with pytest.raises(InvalidRecord):
        event_repo.upsert_camera("CAM_1", "Gate", "", "rtsp://admin:secret@10.0.0.5/stream1", "ACTIVE", {})
    with pytest.raises(InvalidRecord):
        event_repo.upsert_camera("CAM_1", "Gate", "", None, "BROKEN", {})
    event_repo.upsert_camera("CAM_1", "Gate", "", "rtsp://10.0.0.5/stream1", "ACTIVE", {})
    assert event_repo.get_camera("CAM_1")["rtsp_url"] == "rtsp://10.0.0.5/stream1"


def test_listing_filters_ordering_and_paging(event_repo):
    seed(event_repo, "CAM_1")
    seed(event_repo, "CAM_2")
    for i in range(6):
        event_repo.store(to_record(zone_event(i, cam="CAM_1" if i % 2 == 0 else "CAM_2", severity="HIGH" if i < 3 else "LOW")))
    event_repo.store(to_record(plate_event(10, plate="KA01AB1234")))
    newest_first = [r["timestamp"] for r in event_repo.list_events()]
    assert newest_first == sorted(newest_first, reverse=True) and len(newest_first) == 7
    assert event_repo.count_events(camera_id="CAM_2") == 3
    assert event_repo.count_events(severity="LOW") == 3 and event_repo.count_events(event_type="PLATE_RECOGNIZED") == 1
    assert event_repo.count_events(plate="KA01AB1234") == 1
    assert event_repo.count_events(since=utc(T0 + 3), until=utc(T0 + 5)) == 2                     # since inclusive, until exclusive
    page1, page2 = event_repo.list_events(limit=3, offset=0), event_repo.list_events(limit=3, offset=3)
    assert len(page1) == 3 and len(page2) == 3 and not {r["event_id"] for r in page1} & {r["event_id"] for r in page2}
    assert len(event_repo.list_events(limit=10**6)) == 7                                            # the page size is capped, not an error


# ----------------------------------------------------------------------------- alerts
def test_a_threat_alert_creates_an_alert_with_a_history_entry(event_repo):
    seed(event_repo)
    e = alert_event(2, score=60, level="HIGH", alert_id="ALR_1", entity="CAM_1#7")
    event_repo.store(to_record(e))
    a = event_repo.get_alert("ALR_1")
    assert (a["status"], a["priority"], a["threat_score"], a["camera_id"], a["entity"]) == ("NEW", "HIGH", 60, "CAM_1", "CAM_1#7")
    assert a["event_id"] == e.event_id and a["acknowledged_by"] is None and a["created_at"] == utc(T0 + 2)
    history = event_repo.alert_history("ALR_1")
    assert [(h["from_status"], h["to_status"], h["actor"]) for h in history] == [(None, "NEW", "system")]


def test_alert_counters_cover_every_priority(event_repo):
    seed(event_repo)
    for i, (level, score) in enumerate([("LOW", 10), ("MEDIUM", 40), ("HIGH", 60), ("HIGH", 70), ("CRITICAL", 100)]):
        event_repo.store(to_record(alert_event(i, score=score, level=level, alert_id=f"A{i}")))
    event_repo.transition_alert("A2", "ACKNOWLEDGED", "operator1")
    event_repo.transition_alert("A3", "RESOLVED", "operator1")
    counts = event_repo.alert_counts()
    assert counts["CRITICAL"] == {"total": 1, "new": 1, "open": 1}
    assert counts["HIGH"] == {"total": 2, "new": 0, "open": 1}
    assert counts["LOW"]["total"] == 1 and set(counts) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_alerts_list_newest_first_with_filters(event_repo):
    seed(event_repo)
    for i in range(4):
        event_repo.store(to_record(alert_event(i, level="HIGH" if i % 2 else "LOW", alert_id=f"A{i}")))
    event_repo.transition_alert("A3", "ACKNOWLEDGED", "op")
    assert [a["alert_id"] for a in event_repo.list_alerts()] == ["A3", "A2", "A1", "A0"]
    assert [a["alert_id"] for a in event_repo.list_alerts(priority="HIGH")] == ["A3", "A1"]
    assert [a["alert_id"] for a in event_repo.list_alerts(status="ACKNOWLEDGED")] == ["A3"]


def test_the_workflow_records_who_decided_and_when(event_repo):
    seed(event_repo)
    event_repo.store(to_record(alert_event(1, alert_id="A1")))
    a = event_repo.transition_alert("A1", "ACKNOWLEDGED", "officer.rao", "on it")
    assert a["status"] == "ACKNOWLEDGED" and a["acknowledged_by"] == "officer.rao" and a["acknowledged_at"] is not None
    a = event_repo.transition_alert("A1", "IN_PROGRESS", "officer.rao")
    a = event_repo.transition_alert("A1", "RESOLVED", "officer.sen", "patrol checked, no issue")
    assert a["status"] == "RESOLVED" and a["resolved_at"] is not None and a["acknowledged_by"] == "officer.rao"
    history = event_repo.alert_history("A1")
    assert [(h["from_status"], h["to_status"], h["actor"]) for h in history] == [
        (None, "NEW", "system"), ("NEW", "ACKNOWLEDGED", "officer.rao"),
        ("ACKNOWLEDGED", "IN_PROGRESS", "officer.rao"), ("IN_PROGRESS", "RESOLVED", "officer.sen")]
    assert history[1]["note"] == "on it"


@pytest.mark.parametrize("sequence", [
    [("RESOLVED", "ok"), ("ACKNOWLEDGED", "late")],               # a final status cannot be changed
    [("FALSE_POSITIVE", "ok"), ("RESOLVED", "late")],
    [("ACKNOWLEDGED", "ok"), ("ACKNOWLEDGED", "again")],          # no repeats
    [("IN_PROGRESS", "ok"), ("ACKNOWLEDGED", "backwards")],       # no going backwards
])
def test_invalid_transitions_are_refused_and_change_nothing(event_repo, sequence):
    seed(event_repo)
    event_repo.store(to_record(alert_event(1, alert_id="A1")))
    (first, _), (second, _) = sequence
    event_repo.transition_alert("A1", first, "op")
    before = event_repo.get_alert("A1")
    with pytest.raises(InvalidTransition):
        event_repo.transition_alert("A1", second, "op")
    assert event_repo.get_alert("A1")["status"] == before["status"] and len(event_repo.alert_history("A1")) == 2


def test_transitions_need_a_person_a_known_alert_and_a_valid_target(event_repo):
    seed(event_repo)
    event_repo.store(to_record(alert_event(1, alert_id="A1")))
    for actor in ("", "   ", None):
        with pytest.raises(InvalidTransition):
            event_repo.transition_alert("A1", "ACKNOWLEDGED", actor)
    with pytest.raises(InvalidTransition):
        event_repo.transition_alert("A1", "NEW", "op")
    with pytest.raises(InvalidTransition):
        event_repo.transition_alert("A1", "EXPLODED", "op")
    with pytest.raises(AlertNotFound):
        event_repo.transition_alert("NOPE", "ACKNOWLEDGED", "op")
    assert event_repo.get_alert("A1")["status"] == "NEW"


def test_two_operators_acknowledging_at_once_get_one_winner(event_repo):
    seed(event_repo)
    event_repo.store(to_record(alert_event(1, alert_id="A1")))
    outcomes = []

    def go(name):
        try:
            event_repo.transition_alert("A1", "ACKNOWLEDGED", name)
            outcomes.append("ok")
        except InvalidTransition:
            outcomes.append("refused")

    threads = [threading.Thread(target=go, args=(f"op{i}",)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert outcomes.count("ok") == 1 and outcomes.count("refused") == 5
    assert len(event_repo.alert_history("A1")) == 2


# ----------------------------------------------------------------------------- vehicles and detections
def test_plate_sightings_are_stored_and_searchable(event_repo):
    seed(event_repo)
    seed(event_repo, "CAM_2")
    for i, (plate, cam) in enumerate([("KA01AB1234", "CAM_1"), ("KA01AB1234", "CAM_2"), ("MH12DE1433", "CAM_1")]):
        assert event_repo.store(to_record(plate_event(i, plate=plate, cam=cam))).vehicle_created
    rows = event_repo.list_vehicles(plate="KA01AB1234")
    assert [r["camera_id"] for r in rows] == ["CAM_2", "CAM_1"] and len(event_repo.list_vehicles()) == 3
    assert all(0.0 <= r["confidence"] <= 1.0 for r in rows)


def test_a_track_summary_is_stored_as_one_detection_row(event_repo):
    seed(event_repo)
    e = summary_event(0, cls="person", hits=40, duration=12.0)
    assert event_repo.store(to_record(e)).detection_created
    assert not event_repo.store(to_record(e)).inserted
    rows = event_repo.list_detections(camera_id="CAM_1")
    assert len(rows) == 1 and rows[0]["object_type"] == "person" and rows[0]["hits"] == 40
    assert event_repo.list_detections(camera_id="CAM_2") == []


# ----------------------------------------------------------------------------- retention and stats
def test_purge_follows_the_retention_policy(event_repo):
    seed(event_repo)
    old, new = T0, T0 + 40 * 86400
    event_repo.store(to_record(zone_event(0)))                                       # old plain event
    event_repo.store(to_record(plate_event(1)))                                      # old event with a vehicle row
    event_repo.store(to_record(alert_event(2, alert_id="OLD")))
    e_new = zone_event(0, ts=new)
    event_repo.store(to_record(e_new))
    cutoff_events, cutoff_alerts = utc(T0 + 20 * 86400), utc(T0 + 10)
    deleted = event_repo.purge(cutoff_events, cutoff_alerts)
    assert deleted == {"alerts": 1, "events": 3}                                      # the old alert goes first, then its old events
    assert event_repo.count_events() == 1 and event_repo.get_event(e_new.event_id) is not None
    assert event_repo.list_vehicles() == [] and event_repo.get_alert("OLD") is None


def test_an_old_event_is_kept_while_a_retained_alert_still_needs_it(event_repo):
    seed(event_repo)
    event_repo.store(to_record(alert_event(2, alert_id="KEEP")))                      # alert at T0 + 2
    deleted = event_repo.purge(utc(T0 + 86400), utc(T0 - 86400))                      # events expire, alerts do not
    assert deleted == {"alerts": 0, "events": 0} and event_repo.get_alert("KEEP") is not None


def test_stats_summarize_the_tables(event_repo):
    seed(event_repo)
    event_repo.store(to_record(zone_event(1)))
    event_repo.store(to_record(alert_event(2, alert_id="A1")))
    s = event_repo.stats()
    assert (s["events"], s["alerts"], s["cameras"]) == (2, 1, 1)
    assert s["oldest_event"] == utc(T0 + 1) and s["newest_event"] == utc(T0 + 2)
