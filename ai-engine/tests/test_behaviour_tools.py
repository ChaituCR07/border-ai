import pytest

from app.behaviour.engine import BehaviourEngine
from app.behaviour.expect import compare_counts
from app.behaviour.replay import event_from_dict, replay
from behaviour_helpers import epoch, make_cfg, make_rule, obs

T0 = epoch("2026-10-12 02:13:00")


def loiter_rule():
    return make_rule("R3", [{"type": "zone", "zone_type": "any", "min_dwell_s": 60}], "LOITERING_VIOLATION", "MEDIUM", 15)


def test_replay_reproduces_a_loitering_episode_from_recorded_observations():
    events = [obs("ZONE_ENTER", T0, track=7), obs("ZONE_EXIT", T0 + 90, track=7)]
    out = replay(events, BehaviourEngine(make_cfg([loiter_rule()])))
    assert [e.type for e in out] == ["LOITERING_VIOLATION"]
    assert 59 <= out[0].timestamp - T0 <= 62


def test_replay_does_not_fire_for_a_short_stay_and_skips_recorded_behaviour_events():
    events = [obs("ZONE_ENTER", T0, track=7), obs("ZONE_EXIT", T0 + 30, track=7),
              obs("ZONE_VIOLATION", T0 + 5, track=7, rule_id="R1", rule_kind="behaviour")]
    assert replay(events, BehaviourEngine(make_cfg([loiter_rule()]))) == []


def test_replay_lets_you_compare_rule_sets_on_the_same_recording():
    events = [obs("ZONE_ENTER", T0, track=7), obs("ZONE_EXIT", T0 + 40, track=7)]
    strict = make_cfg([make_rule("R3", [{"type": "zone", "zone_type": "any", "min_dwell_s": 60}], "LOITERING_VIOLATION")])
    relaxed = make_cfg([make_rule("R3", [{"type": "zone", "zone_type": "any", "min_dwell_s": 20}], "LOITERING_VIOLATION")])
    assert len(replay(events, BehaviourEngine(strict))) == 0
    assert len(replay(events, BehaviourEngine(relaxed))) == 1


def test_event_from_dict_round_trips_the_fields_the_engine_needs():
    original = obs("ZONE_ENTER", T0, track=3, cls="car", rule_id="Z1", rule_type="restricted")
    again = event_from_dict(original.to_dict())
    assert (again.type, again.track_id, again.object_class, again.rule_id, again.rule_type) == \
        ("ZONE_ENTER", 3, "car", "Z1", "restricted")
    assert abs(again.timestamp - T0) < 0.01


def test_compare_counts():
    rows, ok = compare_counts({"A:R1": 1, "B:R2": 2}, {"A:R1": 1, "B:R2": 1})
    assert not ok and [r["pass"] for r in rows] == [True, False]
    assert compare_counts({"A:R1": 2}, {"A:R1": 1}, tolerance=1)[1]
    assert not compare_counts({}, {"A:R1": 1})[1]                               # an expected event that never happened


@pytest.mark.slow
def test_hundreds_of_tracks_keep_memory_bounded():
    from behaviour_helpers import Scene
    rules = [make_rule("R1", [{"type": "zone", "zone_type": "any"}], "ZONE_VIOLATION"),
             make_rule("R4", [{"type": "time", "between": ["22:00", "05:00"]}], "AFTER_HOURS_ACTIVITY")]
    s = Scene(rules, start="2026-10-12 02:00:00")
    for step in range(200):
        tracks = tuple((t, "person") for t in range(step, step + 50))              # a sliding window of 50 tracks
        events = [obs("ZONE_ENTER", s.t, track=t) for t in range(step + 49, step + 50)]
        s.step(tracks=tracks, events=events, removed=[step - 1] if step else [])
    assert s.engine.status()["contexts"] <= 60 and s.engine.stats["evaluations"] > 0
