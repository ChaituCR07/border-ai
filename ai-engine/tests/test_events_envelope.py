import json

import pytest

from app.events.envelope import (SCHEMA_VERSION, InvalidEnvelope, envelope_from_dict, envelope_from_event,
                                 parse_envelope)
from events_helpers import ev


def good_fields():
    return envelope_from_event(ev(1, severity="HIGH"), run_id="RUN1").to_fields()


def test_the_envelope_carries_the_plans_fields():
    e = ev(1, severity="HIGH")
    env = envelope_from_event(e, run_id="RUN1")
    assert env.v == SCHEMA_VERSION and env.event_id == e.event_id and env.type == "ZONE_VIOLATION"
    assert env.camera == "CAM_1" and env.severity == "HIGH" and env.run_id == "RUN1"
    data = env.data
    for key in ("event_id", "camera", "type", "track_id", "timestamp"):
        assert key in data                                         # the plan's example fields
    assert data["camera"] == "CAM_1" and data["camera_id"] == "CAM_1"
    assert data["timestamp"].endswith("Z") and env.ts_ms == 1_000_001_000


def test_plate_and_score_are_visible_at_the_top_level_like_the_plan_example():
    from app.schemas.events import Event
    e = Event(type="WATCHLIST_MATCH", camera_id="CAM_03", timestamp=1_700_000_000.0, frame_id=1, track_id=42,
              object_class="car", confidence=0.91, bbox=(0, 0, 1, 1), rule_id="WATCHLIST", rule_name="w",
              rule_kind="watchlist", rule_type="vehicle", details={"plate": "KA01AB1234", "score": 91})
    d = envelope_from_event(e).data
    assert (d["type"], d["track_id"], d["plate"], d["score"], d["camera"]) == ("WATCHLIST_MATCH", 42, "KA01AB1234", 91, "CAM_03")


def test_fields_are_flat_strings_and_round_trip():
    fields = good_fields()
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in fields.items())
    again = parse_envelope(fields)
    assert again.event_id == fields["event_id"] and again.data["type"] == "ZONE_VIOLATION"
    assert again.to_fields() == fields


def test_event_ids_are_stable_across_conversions():
    e = ev(1)
    assert envelope_from_event(e).event_id == envelope_from_event(e).event_id == e.event_id


def test_journal_lines_convert_to_the_same_envelope():
    e = ev(2, "THREAT_ALERT", severity="CRITICAL")
    from_event = envelope_from_event(e)
    from_line = envelope_from_dict(json.loads(json.dumps(e.to_dict())))
    assert (from_line.event_id, from_line.type, from_line.camera, from_line.ts_ms, from_line.severity) == \
        (from_event.event_id, from_event.type, from_event.camera, from_event.ts_ms, from_event.severity)


@pytest.mark.parametrize("mutate, reason", [
    (lambda f: f.pop("v"), "missing_or_invalid_version"),
    (lambda f: f.update(v="abc"), "missing_or_invalid_version"),
    (lambda f: f.update(v="2"), "unsupported_version:2"),
    (lambda f: f.pop("data"), "missing_data"),
    (lambda f: f.update(data="{not json"), "data_not_json"),
    (lambda f: f.update(data="[1,2]"), "data_not_an_object"),
    (lambda f: f.update(data="x" * 70000), "data_too_large"),
    (lambda f: f.update(event_id=""), "invalid_event_id"),
    (lambda f: f.update(event_id="x" * 65), "invalid_event_id"),
    (lambda f: f.update(type="zone violation"), "invalid_type"),
    (lambda f: f.update(camera=""), "invalid_camera"),
    (lambda f: f.update(ts="yesterday"), "invalid_timestamp"),
    (lambda f: f.update(event_id="OTHER"), "envelope_and_data_disagree"),
    (lambda f: f.update(type="LINE_CROSSING"), "envelope_and_data_disagree"),
])
def test_invalid_messages_are_rejected_with_a_reason(mutate, reason):
    fields = good_fields()
    mutate(fields)
    with pytest.raises(InvalidEnvelope, match=reason):
        parse_envelope(fields)


def test_a_payload_without_track_id_or_with_a_bad_timestamp_is_rejected():
    for patch, reason in ((lambda d: d.pop("track_id"), "missing_track_id"),
                          (lambda d: d.update(timestamp="not a time"), "invalid_data_timestamp")):
        fields = good_fields()
        data = json.loads(fields["data"])
        patch(data)
        fields["data"] = json.dumps(data)
        with pytest.raises(InvalidEnvelope, match=reason):
            parse_envelope(fields)
