"""Known-answer unit tests for ANPR alignment, CER, exact matching, and confusion analysis."""
from evaluation.anpr.metrics import (
    align,
    confusion,
    corpus_metrics,
    plate_key,
    plate_norm,
    score_pair,
)


def test_plate_norm_and_key() -> None:
    assert plate_norm("ka 01-ab.1234") == "KA01AB1234"
    assert plate_norm("DL-10-C-A-1234") == "DL10CA1234"
    assert plate_norm("") == ""
    assert plate_norm(None) == ""

    # Confusables mapping: OQDIBSZG -> 00018526
    assert plate_key("KA01AB1234") == "KA01A81234"  # B -> 8
    assert plate_key("KAOIAB1234") == "KA01A81234"  # O -> 0, I -> 1, B -> 8
    assert plate_key("MH12DE1433") == "MH120E1433"  # D -> 0


def test_align_known_cases() -> None:
    # 1. Perfect match
    dist, ops = align("KA01AB1234", "KA01AB1234")
    assert dist == 0
    assert len(ops) == 10
    assert all(op == "match" for op, _, _ in ops)

    # 2. Single substitution (1 -> I)
    dist, ops = align("KA01AB1234", "KA0IAB1234")
    assert dist == 1
    sub_ops = [(op, g, p) for op, g, p in ops if op == "sub"]
    assert len(sub_ops) == 1
    assert sub_ops[0] == ("sub", "1", "I")

    # 3. Deletion (last char dropped)
    dist, ops = align("KA01AB1234", "KA01AB123")
    assert dist == 1
    assert ("del", "4", "") in ops

    # 4. Insertion (extra char at end)
    dist, ops = align("KA01AB1234", "KA01AB12345")
    assert dist == 1
    assert ("ins", "", "5") in ops


def test_align_deterministic_tie_breaking() -> None:
    # Multiple runs on same string must produce identical operations
    dist1, ops1 = align("ABCDEF", "AZCXEF")
    dist2, ops2 = align("ABCDEF", "AZCXEF")
    assert dist1 == dist2
    assert ops1 == ops2


def test_score_pair_exact_near_miss_and_lookalike() -> None:
    # Exact
    res = score_pair("KA01AB1234", "KA01AB1234")
    assert res["exact"] is True
    assert res["near_miss"] is False
    assert res["lookalike_equiv"] is True
    assert res["emitted"] is True
    assert res["edit_distance"] == 0

    # Near-miss and look-alike equivalent (1 -> I)
    res = score_pair("KA01AB1234", "KA0IAB1234")
    assert res["exact"] is False
    assert res["near_miss"] is True
    assert res["lookalike_equiv"] is True
    assert res["edit_distance"] == 1

    # Near-miss but NOT look-alike (4 -> 5)
    res = score_pair("KA01AB1234", "KA01AB1235")
    assert res["exact"] is False
    assert res["near_miss"] is True
    assert res["lookalike_equiv"] is False
    assert res["edit_distance"] == 1

    # Empty prediction
    res = score_pair("KA01AB1234", None)
    assert res["exact"] is False
    assert res["near_miss"] is False
    assert res["lookalike_equiv"] is False
    assert res["emitted"] is False
    assert res["edit_distance"] == 10

    # Empty GT raises ValueError
    raised = False
    try:
        score_pair("", "KA01AB1234")
    except ValueError:
        raised = True
    assert raised is True


def test_corpus_metrics_micro_averaging() -> None:
    # Pair 1: len 10, dist 1
    # Pair 2: len 4, dist 1
    # Total chars = 14, total errors = 2
    # Micro CER = 2 / 14 = 0.142857 -> char_accuracy = 12 / 14 ≈ 0.857143
    # (Macro CER would be (1/10 + 1/4)/2 = 0.175)
    pairs = [
        score_pair("KA01AB1234", "KA01AB1235"),  # dist 1
        score_pair("KA01", "KA02"),              # dist 1
    ]
    metrics = corpus_metrics(pairs)
    assert abs(metrics["char_accuracy"] - (12.0 / 14.0)) < 1e-5
    assert metrics["plate_exact"] == 0.0
    assert metrics["near_miss"] == 1.0
    assert metrics["read_rate"] == 1.0


def test_confusion_counter() -> None:
    pairs = [
        score_pair("KA01AB1234", "KA0IAB1234"),   # 1 -> I
        score_pair("KA01AB1234", "KA01A81234"),   # B -> 8
        score_pair("KA01", "KA0"),                # del 1 -> ∅
        score_pair("KA01", "KA019"),               # ins ∅ -> 9
    ]
    c = confusion(pairs)
    assert c[("1", "I")] == 1
    assert c[("B", "8")] == 1
    assert c[("1", "∅")] == 1
    assert c[("∅", "9")] == 1
