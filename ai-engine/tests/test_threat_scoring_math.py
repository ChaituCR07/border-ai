import itertools
import random

from app.threat.scoring import total_score
from threat_helpers import make_scoring

CFG = make_scoring()


def test_plan_scenario_1_arithmetic():
    r = total_score({"line_crossing": 20, "zone_violation": 30, "after_hours": 10}, CFG)
    assert (r.score, r.bonus, r.capped) == (60, 0, False)
    assert CFG.level_for(r.score) == "HIGH"


def test_plan_scenario_2_and_the_day_12_example_reach_100_and_are_capped():
    r = total_score({"watchlist_vehicle": 40, "zone_violation": 30, "direction_violation": 20, "after_hours": 10}, CFG)
    assert (r.score, r.raw, r.bonus, r.capped) == (100, 110, 10, True)
    assert CFG.level_for(r.score) == "CRITICAL"


def test_the_plan_section_5_evidence_without_an_unknown_person_weight_gives_55():
    r = total_score({"zone_violation": 30, "after_hours": 10, "loitering": 15}, CFG)
    assert r.score == 55 and CFG.level_for(55) == "MEDIUM"


def test_the_bonus_needs_enough_distinct_kinds():
    assert total_score({"a": 10, "b": 10, "c": 10}, CFG).bonus == 0
    assert total_score({"a": 10, "b": 10, "c": 10, "d": 10}, CFG).bonus == 10
    relaxed = make_scoring(bonus={"multiple_suspicious": {"points": 5, "min_distinct_kinds": 2}})
    assert total_score({"a": 10, "b": 10}, relaxed).score == 25


def test_a_wrong_way_crossing_counts_once():
    r = total_score({"line_crossing": 20, "direction_violation": 20}, CFG)
    assert r.score == 20 and r.excluded == ["line_crossing"] and r.counted == {"direction_violation": 20}
    assert total_score({"line_crossing": 20}, CFG).score == 20                  # a permitted crossing still counts


def test_zero_point_kinds_are_ignored_and_nothing_scores_zero():
    assert total_score({"zone_violation": 0}, CFG).score == 0
    assert total_score({}, CFG).score == 0


def test_the_cap_is_configurable():
    cfg = make_scoring(max_score=50, levels=[{"name": "LOW", "min": 0}, {"name": "MEDIUM", "min": 10},
                                             {"name": "HIGH", "min": 20}, {"name": "CRITICAL", "min": 40}])
    r = total_score({"a": 40, "b": 40}, cfg)
    assert r.score == 50 and r.capped


def test_the_score_never_depends_on_the_order_of_the_evidence():
    kinds = {"zone_violation": 30, "after_hours": 10, "line_crossing": 20, "watchlist_vehicle": 40, "loitering": 15}
    expected = total_score(kinds, CFG).score
    for perm in itertools.permutations(kinds.items()):
        assert total_score(dict(perm), CFG).score == expected


def test_adding_evidence_never_lowers_the_score_and_the_score_never_exceeds_the_cap():
    rng = random.Random(4)
    names = ["zone_violation", "after_hours", "loitering", "watchlist_vehicle", "watchlist_person", "unauthorized_vehicle_night"]
    for _ in range(300):
        base = {n: rng.choice([0, 10, 20, 30, 40, 50]) for n in rng.sample(names, rng.randint(0, 5))}
        extra = dict(base)
        extra[rng.choice(names)] = rng.choice([10, 30, 50])
        for k, v in base.items():
            extra[k] = max(extra.get(k, 0), v)
        a, b = total_score(base, CFG), total_score(extra, CFG)
        assert b.score >= a.score and 0 <= b.score <= CFG.max_score


def test_the_level_never_decreases_as_the_score_increases():
    levels = [CFG.level_for(s) for s in range(0, 101)]
    ranks = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    assert all(ranks[a] <= ranks[b] for a, b in zip(levels, levels[1:]))
