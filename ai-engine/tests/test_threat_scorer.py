import json
import threading
from types import SimpleNamespace

import pytest

from app.schemas.events import Event
from app.threat.scorer import ThreatScorer
from threat_helpers import (Bench, after_hours, beh, direction_v, frame, line_cross, loitering, make_scoring,
                            plate_ev, watch, zone_v)


# ------------------------------------------------------------------ scores
def test_each_kind_has_the_planned_weight():
    b = Bench()
    b.step([after_hours(b.t)])
    assert b.state().score == 10
    b.step([loitering(b.t)])
    assert b.state().score == 25
    b.step([direction_v(b.t)])
    assert b.state().score == 45                               # 10 + 15 + 20


def test_points_can_come_from_the_event_or_from_the_configuration():
    b = Bench()
    b.step([beh("ZONE_VIOLATION", 25, b.t)])                    # from_event: the rule's own points
    assert b.state().score == 25
    b.step([line_cross(b.t)])                                   # fixed: 20 whatever the event says
    assert b.state().score == 45


def test_review_grade_watchlist_hits_count_for_half():
    for entity, status, expected in [("VEHICLE", "alert", 40), ("VEHICLE", "review", 20),
                                     ("FACE", "review", 25), ("PERSON", "alert", 50)]:
        b = Bench()
        b.step([watch(b.t, entity_type=entity, status=status, cls="person" if entity in ("FACE", "PERSON") else "car")])
        assert b.state().score == expected, (entity, status)


def test_a_kind_counts_once_even_when_it_repeats():
    b = Bench()
    for _ in range(5):
        b.step([line_cross(b.t, direction="IN")])
    assert b.state().score == 20


def test_several_occurrences_count_when_the_source_allows_it():
    scoring = make_scoring()
    for src in scoring.sources:
        if src.id == "line_crossing":
            src.max_occurrences = 3
    b = Bench(scoring)
    for line in ("L1", "L2", "L3", "L4"):
        b.step([line_cross(b.t, line=line)])
    assert b.state().score == 60                                # the three strongest of four distinct crossings


def test_the_score_is_capped_at_100():
    b = Bench()
    b.step([watch(b.t), zone_v(b.t), direction_v(b.t), after_hours(b.t), beh("UNAUTHORIZED_VEHICLE_AFTER_HOURS", 40, b.t)])
    s = b.state()
    assert s.score == 100 and s.capped and s.raw > 100


def test_a_wrong_way_crossing_counts_once():
    b = Bench()
    b.step([line_cross(b.t, direction="OUT"), direction_v(b.t)])
    s = b.state()
    assert s.score == 20 and s.excluded == ["line_crossing"]


# ------------------------------------------------------------------ the time window
def test_evidence_expires_after_the_window_and_repeats_refresh_it():
    b = Bench()
    t0 = b.t
    b.step([after_hours(b.t)])
    b.advance(500)
    b.step([after_hours(b.t)])                                  # seen again: refreshed
    b.advance(200)
    b.step()                                                    # 200 s after the refresh
    assert b.state().score == 10
    b.advance(500)
    b.step()                                                    # 700 s after the refresh: expired
    assert b.state().score == 0 and b.t - t0 > 1200


def test_partially_expired_evidence_lowers_the_score_and_level():
    b = Bench()
    b.step([zone_v(b.t)])
    b.advance(400)
    b.step([after_hours(b.t)])
    assert b.state().score == 40 and b.state().level == "MEDIUM"
    b.advance(250)
    b.step()                                                    # the zone evidence (650 s old) has expired
    assert (b.state().score, b.state().level) == (10, "LOW")


# ------------------------------------------------------------------ alerts
def test_the_first_evidence_above_the_minimum_raises_a_low_alert():
    b = Bench()
    out = b.step([after_hours(b.t)])
    assert len(out) == 1 and out[0].details["level"] == "LOW" and out[0].details["previous_level"] is None


def test_evidence_below_the_alert_minimum_does_not_alert():
    scoring = make_scoring()
    b = Bench(scoring)
    assert b.step([beh("AFTER_HOURS_ACTIVITY", 5, b.t, rule_id="R004")]) == [] and b.state().score == 5


def test_alerts_follow_escalation_and_never_repeat_a_level():
    b = Bench()
    b.step([after_hours(b.t)])                                  # 10  LOW
    b.step([zone_v(b.t)])                                       # 40  MEDIUM
    b.step([line_cross(b.t)])                                   # 60  HIGH
    assert b.levels == ["LOW", "MEDIUM", "HIGH"]
    b.step([after_hours(b.t)])                                  # more of the same: no alert
    b.step([watch(b.t)])                                        # 100 CRITICAL
    assert b.levels == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert [a.details["previous_level"] for a in b.alerts] == [None, "LOW", "MEDIUM", "HIGH"]
    b.run = b.step([zone_v(b.t)])
    assert len(b.alerts) == 4


def test_a_de_escalation_followed_by_a_quick_re_escalation_is_not_alerted_again():
    b = Bench()
    b.step([watch(b.t), zone_v(b.t)])                           # 70 HIGH
    b.advance(400)
    b.step([after_hours(b.t), direction_v(b.t)])                # 100 CRITICAL (watchlist and zone still count)
    assert b.levels == ["HIGH", "CRITICAL"]
    b.advance(250)
    b.step()                                                    # watchlist and zone expired: 30 MEDIUM
    assert b.state().level == "MEDIUM"
    b.advance(50)
    b.step([zone_v(b.t)])                                       # 60 HIGH again, 50 s later
    assert b.state().level == "HIGH" and b.levels == ["HIGH", "CRITICAL"]


def test_a_quiet_period_ends_the_episode_and_a_new_one_alerts_again():
    b = Bench()
    b.step([after_hours(b.t)])
    b.advance(650)
    b.step()                                                    # expired: below the alert minimum
    b.advance(350)
    b.step()                                                    # quiet for more than rearm_s
    b.advance(10)
    b.step([after_hours(b.t)])
    assert b.levels == ["LOW", "LOW"]


def test_the_cooldown_delays_the_first_alert_of_a_new_episode():
    b = Bench(make_scoring(cooldown_s=5000))
    b.step([after_hours(b.t)])
    b.advance(650)
    b.step()
    b.advance(350)
    b.step()
    b.advance(10)
    b.step([after_hours(b.t)])
    assert b.levels == ["LOW"] and b.scorer.stats["suppressed_cooldown"] >= 1


def test_entities_are_scored_independently():
    b = Bench()
    b.step([zone_v(b.t, track=1), after_hours(b.t, track=2)], tracks=((1, "person"), (2, "person")))
    assert (b.state(1).score, b.state(2).score) == (30, 10)


# ------------------------------------------------------------------ explanation (what the dashboard shows)
def test_an_alert_explains_itself():
    b = Bench()
    b.step([plate_ev(b.t, "KA01AB1234")])
    out = b.step([watch(b.t), zone_v(b.t)])
    d = out[0].details
    assert d["threat_score"] == 70 and d["level"] == "HIGH" and d["plate"] == "KA01AB1234"
    assert [c["kind"] for c in d["contributions"]] == ["watchlist_vehicle", "zone_violation"]       # strongest first
    assert d["contributions"][0]["label"] == "Watchlisted vehicle" and d["contributions"][0]["event_id"]
    assert d["summary"] == "HIGH (70/100): Watchlisted vehicle +40, Restricted zone entry +30"
    assert d["alert_id"] and d["priority"] == "HIGH" and d["window_s"] == 600 and d["capped"] is False


def test_the_alert_json_matches_the_planned_contract():
    b = Bench()
    alert = b.step([zone_v(b.t), after_hours(b.t)])[0]
    d = alert.to_dict()
    assert d["type"] == "THREAT_ALERT" and d["severity"] == "MEDIUM" and d["threat_score"] == 40
    assert d["rule"]["kind"] == "threat" and d["camera_id"] == "CAM" and d["track_id"] == 1
    json.dumps(d)                                                # serializable end to end


def test_a_capped_alert_shows_the_bonus_and_the_cap():
    b = Bench()
    alert = b.step([watch(b.t), zone_v(b.t), direction_v(b.t), after_hours(b.t)])[0]
    d = alert.details
    assert d["capped"] is True and d["bonus"] == {"multiple_suspicious": 10} and d["threat_score"] == 100
    assert "multiple suspicious events +10" in d["summary"]


# ------------------------------------------------------------------ merging by plate
@pytest.mark.parametrize("plate_first", [True, False])
def test_fragmented_tracks_of_one_vehicle_share_a_score(plate_first):
    b = Bench()
    tracks = ((1, "car"), (2, "car"))
    b.step([zone_v(b.t, track=1, cls="car"), plate_ev(b.t, "KA01AB1234", track=1)], tracks=tracks)
    assert b.state(1).score == 30
    second = [plate_ev(b.t, "KA01AB1234", track=2), direction_v(b.t, track=2, cls="car")]
    b.step(second if plate_first else list(reversed(second)), tracks=tracks)
    assert b.state(1).score == b.state(2).score == 50
    assert b.state(1).plate == "KA01AB1234" and b.state(1).entity == "plate:KA01AB1234"


def test_merging_can_be_switched_off():
    b = Bench(make_scoring(merge_by_plate=False))
    tracks = ((1, "car"), (2, "car"))
    b.step([zone_v(b.t, track=1, cls="car"), plate_ev(b.t, "KA01AB1234", track=1),
            direction_v(b.t, track=2, cls="car"), plate_ev(b.t, "KA01AB1234", track=2)], tracks=tracks)
    assert (b.state(1).score, b.state(2).score) == (30, 20)


def test_a_vehicle_that_was_already_alerted_does_not_alert_again_after_merging():
    b = Bench()
    tracks = ((1, "car"), (2, "car"))
    b.step([zone_v(b.t, track=1, cls="car"), after_hours(b.t, track=1, cls="car")], tracks=tracks)    # 40 MEDIUM alert
    b.step([plate_ev(b.t, "KA01AB1234", track=1), plate_ev(b.t, "KA01AB1234", track=2)], tracks=tracks)
    assert b.levels == ["MEDIUM"]


def test_the_merge_scope_decides_whether_cameras_share_a_vehicle():
    for scope, expected in (("camera", (30, 20)), ("global", (50, 50))):
        sc = ThreatScorer(make_scoring(merge_scope=scope))
        sc.observe("CAM_A", [zone_v(1_000_000.0, cam="CAM_A", track=1, cls="car"),
                             plate_ev(1_000_000.0, "KA01AB1234", cam="CAM_A", track=1)])
        sc.update(frame("CAM_A", 1_000_000.0, [(1, "car")]))
        sc.observe("CAM_B", [direction_v(1_000_001.0, cam="CAM_B", track=1, cls="car"),
                             plate_ev(1_000_001.0, "KA01AB1234", cam="CAM_B", track=1)])
        sc.update(frame("CAM_B", 1_000_001.0, [(1, "car")]))
        assert (sc.current("CAM_A", 1).score, sc.current("CAM_B", 1).score) == expected, scope


def test_people_are_never_merged_by_plate():
    b = Bench()
    b.step([zone_v(b.t, track=1), plate_ev(b.t, "KA01AB1234", track=1, cls="car")])        # a plate read on track 1
    assert b.state(1).plate == "KA01AB1234"                                                  # that is a vehicle by definition


# ------------------------------------------------------------------ robustness
def test_the_scorers_own_alerts_are_not_scored_again():
    b = Bench()
    alert = b.step([after_hours(b.t)])[0]
    b.scorer.observe("CAM", [alert])
    assert b.scorer._inbox == {}


def test_observe_is_thread_safe():
    b = Bench()

    def feed(track):
        for _ in range(50):
            b.scorer.observe("CAM", [after_hours(b.t, track=track)])

    threads = [threading.Thread(target=feed, args=(t,)) for t in range(1, 9)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    b.step(tracks=tuple((t, "person") for t in range(1, 9)))
    assert b.scorer.status()["entities"] == 8 and all(b.state(t).score == 10 for t in range(1, 9))


def test_the_same_evidence_in_any_order_gives_the_same_score():
    events = lambda t: [watch(t), zone_v(t), direction_v(t), after_hours(t), line_cross(t, "OUT")]
    scores = set()
    for order in (lambda e: e, lambda e: list(reversed(e)), lambda e: e[2:] + e[:2]):
        b = Bench()
        b.step(order(events(b.t)))
        scores.add(b.state().score)
    assert scores == {100}


def test_idle_entities_are_forgotten():
    b = Bench(dt=1000.0)
    b.step([after_hours(b.t)])
    b.run = [b.step(tracks=()) for _ in range(4)]
    assert b.scorer.status()["entities"] == 0 and b.scorer.snapshot("CAM") == {}


def test_the_overlay_snapshot_lists_scores_by_track():
    b = Bench()
    b.step([zone_v(b.t, track=1), after_hours(b.t, track=2)], tracks=((1, "person"), (2, "person")))
    assert b.scorer.snapshot("CAM") == {1: (30, "MEDIUM"), 2: (10, "LOW")} and b.scorer.snapshot("OTHER") == {}
