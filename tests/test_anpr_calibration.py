"""Unit tests for ANPR confidence calibration, ECE, and selective prediction."""
from evaluation.anpr.calibration import (
    confidently_wrong,
    coverage_accuracy,
    ece,
    rule_of_three_upper_bound,
    wilson_score_interval,
)


def test_ece_perfect_and_worst() -> None:
    # 1. Perfectly calibrated: 10 samples in bin [0.8, 0.9] with conf 0.8 and 8/10 correct
    confs = [0.80] * 10
    correct = [True] * 8 + [False] * 2
    assert abs(ece(confs, correct, bins=10)) < 1e-6

    # 2. Worst calibration: conf 1.0, but 0/10 correct -> error = |0.0 - 1.0| = 1.0
    bad_confs = [1.0] * 10
    bad_correct = [False] * 10
    assert abs(ece(bad_confs, bad_correct, bins=10) - 1.0) < 1e-6

    # 3. Empty input
    assert ece([], []) == 0.0


def test_coverage_accuracy_monotonicity_and_endpoints() -> None:
    confs = [0.95, 0.85, 0.70, 0.50]
    correct = [True, True, False, True]

    covs, accs = coverage_accuracy(confs, correct)
    assert len(covs) == 4
    assert len(accs) == 4

    # Coverage strictly increases to 1.0
    assert covs == [0.25, 0.50, 0.75, 1.00]

    # Running accuracies:
    # k=1: 1/1 = 1.0
    # k=2: 2/2 = 1.0
    # k=3: 2/3 ≈ 0.6667
    # k=4: 3/4 = 0.75 (overall accuracy)
    assert accs[0] == 1.0
    assert accs[1] == 1.0
    assert abs(accs[2] - (2.0 / 3.0)) < 1e-5
    assert accs[3] == 0.75


def test_confidently_wrong() -> None:
    confs = [0.95, 0.90, 0.75, 0.60]
    correct = [True, False, False, True]

    # tau = 0.85: 0.95 (True) and 0.90 (False) qualify -> 1 wrong out of 2 -> 0.5
    rate, count = confidently_wrong(confs, correct, tau=0.85)
    assert rate == 0.50
    assert count == 1

    # tau = 0.98: none qualify
    rate_zero, count_zero = confidently_wrong(confs, correct, tau=0.98)
    assert rate_zero == 0.0
    assert count_zero == 0


def test_rule_of_three_upper_bound() -> None:
    # 0 events in 300 trials -> 3 / 300 = 0.01 (1%)
    assert abs(rule_of_three_upper_bound(300) - 0.01) < 1e-6
    assert abs(rule_of_three_upper_bound(100) - 0.03) < 1e-6
    assert rule_of_three_upper_bound(0) == 1.0


def test_wilson_score_interval() -> None:
    lo, hi = wilson_score_interval(100, 100)
    assert lo > 0.95
    assert hi == 1.0

    lo_zero, hi_zero = wilson_score_interval(0, 100)
    assert lo_zero == 0.0
    assert hi_zero < 0.05

    # 50/100 should be centered around 0.50
    lo_mid, hi_mid = wilson_score_interval(50, 100)
    assert 0.39 < lo_mid < 0.42
    assert 0.58 < hi_mid < 0.61
