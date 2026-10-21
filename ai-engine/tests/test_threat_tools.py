import pytest

from app.behaviour.replay import replay
from app.threat.calc import evaluate_items
from app.threat.scorer import ThreatScorer
from behaviour_helpers import epoch, obs
from threat_helpers import after_hours, make_scoring, watch, zone_v

POINTS = {"ZONE_VIOLATION": 30, "DIRECTION_VIOLATION": 20, "LOITERING_VIOLATION": 15, "AFTER_HOURS_ACTIVITY": 10}


def test_the_calculator_reproduces_the_plans_examples():
    scoring = make_scoring()
    s1 = evaluate_items(scoring, POINTS, ["line_crossing", "zone_violation", "after_hours"])
    assert (s1["result"].score, s1["level"]) == (60, "HIGH")
    s2 = evaluate_items(scoring, POINTS, ["watchlist_vehicle:alert", "zone_violation", "direction_violation", "after_hours"])
    assert (s2["result"].score, s2["level"]) == (100, "CRITICAL")
    review = evaluate_items(scoring, POINTS, ["watchlist_vehicle:review"])
    assert review["result"].score == 20


def test_the_calculator_rejects_unknown_kinds_and_unknown_points():
    with pytest.raises(ValueError):
        evaluate_items(make_scoring(), POINTS, ["teleportation"])
    with pytest.raises(ValueError, match="no behaviour rule"):
        evaluate_items(make_scoring(), {}, ["zone_violation"])


def test_score_replay_over_a_recording_with_behaviour_events():
    t0 = epoch("2026-10-12 02:13:00")
    events = [after_hours(t0, track=7), zone_v(t0 + 5, track=7),
              obs("ZONE_EXIT", t0 + 20, track=7, rule_id="Z1")]
    alerts = replay(events, ThreatScorer(make_scoring()), keep_behaviour=True)
    assert [a.details["level"] for a in alerts] in (["LOW", "MEDIUM"], ["MEDIUM"])
    assert alerts and alerts[-1].details["threat_score"] == 40 and alerts[0].details["level"] in ("MEDIUM", "LOW")


def test_replay_without_the_flag_drops_behaviour_events():
    t0 = epoch("2026-10-12 02:13:00")
    assert replay([zone_v(t0, track=7)], ThreatScorer(make_scoring())) == []
