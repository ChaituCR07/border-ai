"""ANPR confidence calibration, Expected Calibration Error (ECE), and selective prediction."""
import math
from typing import List, Sequence, Tuple


def ece(confs: Sequence[float], correct: Sequence[bool], bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) across equal-width confidence bins."""
    if not confs or len(confs) != len(correct):
        return 0.0

    total = len(confs)
    bin_size = 1.0 / bins
    error_sum = 0.0

    for b in range(bins):
        lo = b * bin_size
        hi = (b + 1) * bin_size

        # Bin 0 is closed [0.0, hi]; subsequent bins are half-open (lo, hi]
        bin_indices = []
        for idx, c in enumerate(confs):
            if b == 0:
                if lo <= c <= hi:
                    bin_indices.append(idx)
            else:
                if lo < c <= hi:
                    bin_indices.append(idx)

        m = len(bin_indices)
        if m > 0:
            bin_acc = sum(1 for i in bin_indices if correct[i]) / m
            bin_conf = sum(confs[i] for i in bin_indices) / m
            error_sum += (m / total) * abs(bin_acc - bin_conf)

    return float(error_sum)


def coverage_accuracy(
    confs: Sequence[float], correct: Sequence[bool]
) -> Tuple[List[float], List[float]]:
    """Generates coverage vs accuracy curve sorted by descending confidence.

    Returns:
        coverages: List of coverage fractions from 1/N to 1.0
        accuracies: Running accuracy of top-k predictions
    """
    if not confs or len(confs) != len(correct):
        return [], []

    # Sort descending by confidence (stable tie-breaking)
    indexed = sorted(enumerate(confs), key=lambda x: x[1], reverse=True)
    sorted_correct = [correct[i] for i, _ in indexed]

    n = len(sorted_correct)
    coverages: List[float] = []
    accuracies: List[float] = []

    running_correct = 0
    for k in range(1, n + 1):
        if sorted_correct[k - 1]:
            running_correct += 1
        coverages.append(k / n)
        accuracies.append(running_correct / k)

    return coverages, accuracies


def confidently_wrong(
    confs: Sequence[float], correct: Sequence[bool], tau: float = 0.80
) -> Tuple[float, int]:
    """Computes rate and absolute count of wrong predictions with confidence >= tau."""
    hi_conf_total = 0
    wrong_hi_conf = 0

    for c, is_corr in zip(confs, correct):
        if c >= tau:
            hi_conf_total += 1
            if not is_corr:
                wrong_hi_conf += 1

    rate = (wrong_hi_conf / hi_conf_total) if hi_conf_total > 0 else 0.0
    return float(rate), wrong_hi_conf


def rule_of_three_upper_bound(n_trials: int) -> float:
    """Calculates 95% upper confidence bound for a zero-event outcome (3 / n)."""
    if n_trials <= 0:
        return 1.0
    return min(1.0, 3.0 / float(n_trials))


def wilson_score_interval(
    successes: int, total: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """Computes two-sided Wilson score confidence interval for a binomial proportion."""
    if total <= 0:
        return 0.0, 0.0

    # z = 1.96 for 95% confidence
    z = 1.959963984540054 if abs(confidence - 0.95) < 1e-4 else 1.96
    p_hat = successes / total
    z2 = z * z
    denom = 1.0 + (z2 / total)
    center = (p_hat + (z2 / (2.0 * total))) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))

    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return lo, hi
