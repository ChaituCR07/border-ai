import pytest

from app.db.records import MappingError, map_envelope
from app.events.envelope import envelope_from_event
from app.schemas.events import Event
from db_helpers import T0, alert_event, plate_event, summary_event, to_record, utc, zone_event


def test_a_behaviour_event_maps_to_an_event_row_only():
    e = zone_event(5, severity="high")
    rec = to_record(e)
    row = rec.event
    assert (row.event_id, row.camera_id, row.event_type, row.track_id) == (e.event_id, "CAM_1", "ZONE_VIOLATION", 1)
    assert row.severity == "HIGH" and row.threat_score is None and row.timestamp == utc(T0 + 5)
    assert row.rule_id == "R001" and row.rule_kind == "behaviour" and row.run_id == "RUN1"
    assert row.metadata["type"] == "ZONE_VIOLATION" and row.metadata["camera"] == "CAM_1"      # the complete event JSON
    assert rec.alert is None and rec.vehicle is None and rec.detection is None


def test_an_unknown_severity_becomes_null_but_the_event_is_kept():
    rec = to_record(zone_event(severity="SPICY"))
    assert rec.event.severity is None and rec.event.metadata["details"]["severity"] == "SPICY"


def test_a_threat_alert_maps_to_an_alert_row_and_carries_the_score():
    rec = to_record(alert_event(3, score=60, level="HIGH", alert_id="ALR_X", entity="plate:KA01AB1234",
                                plate="KA01AB1234"))
    assert rec.event.threat_score == 60 and rec.event.severity == "HIGH" and rec.event.plate_number == "KA01AB1234"
    a = rec.alert
    assert (a.alert_id, a.event_id, a.camera_id, a.priority, a.threat_score) == ("ALR_X", rec.event.event_id, "CAM_1", "HIGH", 60)
    assert a.entity == "plate:KA01AB1234" and a.created_at == utc(T0 + 3)              # the event's time, not the storage time


def test_the_snapshot_path_is_stored_relative_to_the_runs_folder():
    assert to_record(alert_event(snapshot="snapshots/a1.jpg")).event.snapshot_path == "RUN1/snapshots/a1.jpg"
    assert to_record(alert_event(snapshot=None)).event.snapshot_path is None


@pytest.mark.parametrize("patch, message", [
    (lambda d: d.pop("alert_id"), "alert_id"),
    (lambda d: d.update(level="SPICY", priority="SPICY"), "priority"),
    (lambda d: d.update(threat_score="lots"), "threat_score"),
])
def test_an_alert_that_cannot_be_stored_is_a_mapping_error(patch, message):
    e = alert_event()
    patch(e.details)
    with pytest.raises(MappingError, match=message):
        to_record(e)


def test_the_threat_score_is_clamped_to_the_valid_range():
    assert to_record(alert_event(score=130)).event.threat_score == 100


def test_a_recognized_plate_maps_to_a_vehicle_sighting():
    e = plate_event(2, plate="KA01AB1234", confidence=0.87, final=True)
    rec = to_record(e)
    v = rec.vehicle
    assert (v.plate_number, v.camera_id, v.track_id, v.final, v.plate_format) == ("KA01AB1234", "CAM_1", 2, True, "strict")
    assert 0.0 <= v.confidence <= 1.0 and v.timestamp == utc(T0 + 2)
    assert rec.event.plate_number == "KA01AB1234"


def test_a_plate_event_without_a_plate_still_stores_the_event():
    e = plate_event()
    e.details.pop("plate")
    rec = to_record(e)
    assert rec.vehicle is None and rec.event.event_type == "PLATE_RECOGNIZED"


def test_a_track_summary_maps_to_a_detection_row():
    rec = to_record(summary_event(0, cls="person", hits=40, duration=12.0))
    d = rec.detection
    assert (d.object_type, d.track_id, d.hits, d.duration_s) == ("person", 3, 40, 12.0)
    assert d.first_seen == utc(T0) and d.last_seen == utc(T0 + 12.0) and d.timestamp == d.last_seen
    assert 0.0 <= d.confidence <= 1.0


def test_the_plans_example_event_maps_cleanly():
    e = Event(type="WATCHLIST_MATCH", camera_id="CAM_03", timestamp=1_700_000_000.0, frame_id=1, track_id=42,
              object_class="car", confidence=0.91, bbox=(0, 0, 1, 1), rule_id="WATCHLIST", rule_name="w",
              rule_kind="watchlist", rule_type="vehicle", details={"plate": "KA01AB1234", "score": 91})
    row = map_envelope(envelope_from_event(e, "RUN1")).event
    assert (row.event_type, row.camera_id, row.track_id, row.plate_number) == ("WATCHLIST_MATCH", "CAM_03", 42, "KA01AB1234")


def test_a_bad_timestamp_is_a_mapping_error():
    env = envelope_from_event(zone_event(), "RUN1")
    env.data["timestamp"] = "not a time"
    with pytest.raises(MappingError, match="timestamp"):
        map_envelope(env)
