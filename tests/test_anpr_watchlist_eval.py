"""Unit tests for confusion analysis and watchlist collision simulation."""

from evaluation.anpr.confusion_analysis import (
    analyze_character_confusion,
    is_pair_in_plate_key,
)
from evaluation.anpr.metrics import plate_key, score_pair
from evaluation.anpr.watchlist_eval import (
    TRAFFIC_TIERS,
    generate_synthetic_plate_pool,
    simulate_watchlist_collisions,
)


def test_is_pair_in_plate_key():
    """Verify that current look-alike equivalence pairings return True."""
    assert is_pair_in_plate_key("0", "O") is True
    assert is_pair_in_plate_key("0", "D") is True
    assert is_pair_in_plate_key("0", "Q") is True
    assert is_pair_in_plate_key("1", "I") is True
    assert is_pair_in_plate_key("8", "B") is True
    assert is_pair_in_plate_key("5", "S") is True
    assert is_pair_in_plate_key("2", "Z") is True
    assert is_pair_in_plate_key("6", "G") is True

    # Non-equivalence pairs must return False
    assert is_pair_in_plate_key("A", "B") is False
    assert is_pair_in_plate_key("3", "8") is False
    assert is_pair_in_plate_key("C", "G") is False


def test_character_confusion_evidence_analysis():
    """Test full confusion analysis report generation and counts."""
    pairs = [
        score_pair("KA01AB1234", "KA01AB1234", plate_key),  # match
        score_pair("KA01AB1230", "KA01AB123O", plate_key),  # 0 -> O
        score_pair("KA01AB1238", "KA01AB123B", plate_key),  # 8 -> B
        score_pair("DL01AA1111", "DL01AA111I", plate_key),  # 1 -> I
        score_pair("TS09CD5555", "TS09CD555S", plate_key),  # 5 -> S
        score_pair("UP16EF2222", "UP16EF222Z", plate_key),  # 2 -> Z
        score_pair("GJ01GH6666", "GJ01GH666G", plate_key),  # 6 -> G
        score_pair("KA05JK9999", "KA05JK9998", plate_key),  # 9 -> 8 (non-equivalence)
    ]

    report = analyze_character_confusion(pairs)
    assert report.total_substitutions == 7
    assert report.total_insertions == 0
    assert report.total_deletions == 0

    # Look-alike evidence entries
    ev_map = {(e.char_a, e.char_b): e for e in report.lookalike_evidence}
    assert ev_map[("0", "O")].count == 1
    assert ev_map[("8", "B")].count == 1
    assert ev_map[("1", "I")].count == 1
    assert ev_map[("5", "S")].count == 1
    assert ev_map[("2", "Z")].count == 1
    assert ev_map[("6", "G")].count == 1

    # Verify ADR 0039 verdict
    assert "RETAIN_CURRENT_POLICY" in report.adr0039_verdict

    # Check Markdown formatting
    md = report.to_markdown()
    assert "### Character Confusion Evidence & ADR 0039 Audit" in md
    assert "`0` $\\leftrightarrow$ `O`" in md


def test_watchlist_collision_simulation():
    """Test watchlist collision modeling and traffic tier scaling."""
    # Create deliberate collision pairs: KA01AB1230 and KA01AB123O share plate_key
    pool = [
        "KA01AB1230",
        "KA01AB123O",
        "MH12CD5678",
        "MH12CD567B",
        "DL01EF9999",
        "TS09GH4321",
    ]
    # Augment pool
    pool.extend(generate_synthetic_plate_pool(n=500, seed=42))

    report = simulate_watchlist_collisions(pool, watchlist_sizes=(10, 50), num_trials=3, seed=42)

    assert len(report.tiers) == 2
    t10 = report.tiers[0]
    t50 = report.tiers[1]

    assert t10.watchlist_size == 10
    assert t50.watchlist_size == 50

    # Alert scaling across traffic tiers
    assert t10.exact_alerts_per_day_low == t10.exact_collision_prob * TRAFFIC_TIERS["low"]
    assert t10.exact_alerts_per_day_med == t10.exact_collision_prob * TRAFFIC_TIERS["medium"]
    assert t10.exact_alerts_per_day_high == t10.exact_collision_prob * TRAFFIC_TIERS["high"]

    # Look-alike collision probability must be >= exact collision probability
    assert t10.lookalike_collision_prob >= t10.exact_collision_prob
    assert t50.lookalike_collision_prob >= t50.exact_collision_prob

    # Check Markdown report output
    md = report.to_markdown()
    assert "### Watchlist Collision & Operational False Alert Modeling" in md
    assert "Operational Policy Recommendation" in md
