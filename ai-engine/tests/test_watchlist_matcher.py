import random
from datetime import datetime, timezone

import pytest

from app.watchlist.config import WatchlistConfig
from app.watchlist.matcher import (Match, decide_status, find_best, lookup_in_snapshot, ocr_distance,
                                   score_for)
from app.watchlist.models import WatchlistEntry

NOW = datetime.now(timezone.utc)
CFG = WatchlistConfig()


def entry(i, plate, risk="HIGH", etype="VEHICLE"):
    return WatchlistEntry(i, etype, plate, plate, f"n{i}", "", risk, True, "t", NOW, NOW)


# ------------------------------------------------------------------ distance
def test_distance_basics():
    assert ocr_distance("KA01AB1234", "KA01AB1234") == 0.0
    assert ocr_distance("KA01AB1234", "KA01AB1284") == 1.0        # 3 -> 8: not a look-alike pair
    assert ocr_distance("KA01AB1234", "KA01A81234") == 0.5        # B <-> 8: look-alike
    assert ocr_distance("KA01AB1234", "KA0IAB1234") == 0.5        # 1 <-> I
    assert ocr_distance("KA01AB1234", "KA01AB123") is None        # different length


def test_distance_is_symmetric():
    rng = random.Random(3)
    for _ in range(100):
        a = "".join(rng.choice("ABCDEFGH0123456789") for _ in range(10))
        b = "".join(rng.choice("ABCDEFGH0123456789") for _ in range(10))
        assert ocr_distance(a, b) == ocr_distance(b, a)


# ------------------------------------------------------------------ best match
def test_exact_match_wins_and_highest_risk_is_primary():
    low, high = entry(1, "KA01AB1234", "LOW", "PLATE"), entry(2, "KA01AB1234", "CRITICAL", "VEHICLE")
    m = find_best("KA01AB1234", [low, high], [], CFG)
    assert m.match_type == "exact" and m.entry.watchlist_id == 2 and m.also == [1] and m.quality == 1.0


def test_near_match_within_distance():
    m = find_best("KA01AB1284", [], [entry(1, "KA01AB1234")], CFG)
    assert m.match_type == "near" and m.distance == 1.0 and abs(m.quality - 0.8) < 1e-9


def test_lookalike_swaps_are_cheaper():
    m = find_best("KA01A81234", [], [entry(1, "KA01AB1234")], CFG)
    assert m.distance == 0.5 and abs(m.quality - 0.9) < 1e-9


def test_two_plain_substitutions_are_too_far():
    assert find_best("KA01AB1299", [], [entry(1, "KA01AB1234")], CFG) is None


def test_two_lookalike_swaps_are_still_near_but_three_are_not():
    assert find_best("KA0IA81234", [], [entry(1, "KA01AB1234")], CFG).distance == 1.0
    assert find_best("KAOIA81234", [], [entry(1, "KA01AB1234")], CFG) is None


def test_near_matching_can_be_disabled():
    cfg = WatchlistConfig(near_max_distance=0)
    assert find_best("KA01AB1284", [], [entry(1, "KA01AB1234")], cfg) is None


def test_closest_near_candidate_wins_then_higher_risk():
    a, b = entry(1, "KA01AB1294", "LOW"), entry(2, "KA01AB1234", "LOW")       # read: KA01AB1284
    assert find_best("KA01AB1284", [], [a, b], CFG).entry.watchlist_id == 1  # both 1.0, lower id first
    a2 = entry(1, "KA01AB1294", "LOW")
    b2 = entry(2, "KA01AB1244", "CRITICAL")
    assert find_best("KA01AB1284", [], [a2, b2], CFG).entry.watchlist_id == 2   # tie on distance: higher risk


def test_different_length_candidates_never_match():
    assert find_best("KA01AB1234", [], [entry(1, "KA01AB123")], CFG) is None


def test_random_plates_single_mutation_property():
    """One plain substitution is always a near match; two never are."""
    rng = random.Random(11)
    letters, digits = "ABCDEFGHJKLMNPRSTUVWXYZ", "0123456789"

    def plate():
        return (rng.choice(["KA", "MH", "TN"]) + f"{rng.randint(1, 99):02d}" +
                "".join(rng.choice(letters) for _ in range(2)) + f"{rng.randint(1, 9999):04d}")

    def mutate(p, positions):
        chars = list(p)
        for i in positions:
            pool = digits if chars[i].isdigit() else letters
            # choose a different character that is not a look-alike of the original (cost exactly 1.0)
            while True:
                c = rng.choice(pool)
                if c != chars[i] and ocr_distance(chars[i], c) == 1.0:
                    chars[i] = c
                    break
        return "".join(chars)

    for _ in range(200):
        p = plate()
        e = entry(1, p)
        assert find_best(mutate(p, [rng.randrange(10)]), [], [e], CFG) is not None
        i, j = rng.sample(range(10), 2)
        assert find_best(mutate(p, [i, j]), [], [e], CFG) is None


def test_snapshot_lookup_matches_like_the_database_lookup():
    snap = [entry(1, "KA01AB1234"), entry(2, "MH12XY4321")]
    assert lookup_in_snapshot(snap, "MH12XY4321", CFG).match_type == "exact"
    assert lookup_in_snapshot(snap, "KA01AB1284", CFG).match_type == "near"
    assert lookup_in_snapshot(snap, "ZZ99ZZ9999", CFG) is None


# ------------------------------------------------------------------ scoring and status
def test_score_matches_the_plan_example():
    assert score_for(0.91, 1.0) == 91
    assert score_for(0.91, 0.8) == 73
    assert score_for(1.5, 1.0) == 100 and score_for(-1, 1.0) == 0


@pytest.mark.parametrize("match_type, conf, quality, cfg_kw, expected", [
    ("exact", 0.91, 1.0, {}, "alert"),
    ("exact", 0.50, 1.0, {}, "review"),                      # score 50 >= 40 but confidence < 0.70
    ("exact", 0.30, 1.0, {}, None),                          # score 30 < min_score
    ("near", 0.95, 0.8, {}, "review"),                       # near never alerts by default
    ("near", 0.95, 0.8, {"near_can_alert": True}, "alert"),
    ("near", 0.60, 0.8, {"near_can_alert": True}, "review"), # not confident enough
    ("exact", 0.60, 1.0, {"alert_min_confidence": 0.5}, "alert"),
])
def test_status_rules(match_type, conf, quality, cfg_kw, expected):
    cfg = WatchlistConfig(**cfg_kw)
    m = Match(entry(1, "KA01AB1234"), match_type, 0.0 if match_type == "exact" else 1.0, quality)
    assert decide_status(m, conf, score_for(conf, quality), cfg) == expected
