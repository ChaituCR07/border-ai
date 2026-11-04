import random
from typing import Callable, List, Tuple


def bootstrap_ci(
    values: List[float],
    stat_fn: Callable[[List[float]], float] = lambda xs: sum(xs) / len(xs) if xs else 0.0,
    n_resamples: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Tuple[float, float, float]:
    """Computes bootstrap confidence interval (point_estimate, lo, hi)."""
    if not values:
        return 0.0, 0.0, 0.0

    point_estimate = float(stat_fn(values))
    if len(values) == 1:
        return point_estimate, point_estimate, point_estimate

    rng = random.Random(seed)
    m = len(values)
    resample_stats = []

    for _ in range(n_resamples):
        sample = [values[rng.randint(0, m - 1)] for _ in range(m)]
        resample_stats.append(stat_fn(sample))

    resample_stats.sort()
    lo_idx = int((alpha / 2.0) * n_resamples)
    hi_idx = int((1.0 - alpha / 2.0) * n_resamples)
    hi_idx = min(hi_idx, n_resamples - 1)

    return point_estimate, float(resample_stats[lo_idx]), float(resample_stats[hi_idx])


def bootstrap_ratio_ci(
    numerators: List[float],
    denominators: List[float],
    n_resamples: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Tuple[float, float, float]:
    """Resamples across items (e.g. images) and computes ratio sum(num)/sum(den) to prevent per-image ratio distortion."""
    if not numerators or not denominators or len(numerators) != len(denominators):
        return 0.0, 0.0, 0.0

    total_den = sum(denominators)
    point_estimate = sum(numerators) / total_den if total_den > 0 else 0.0

    m = len(numerators)
    rng = random.Random(seed)
    resample_ratios = []

    for _ in range(n_resamples):
        s_num = 0.0
        s_den = 0.0
        for _ in range(m):
            idx = rng.randint(0, m - 1)
            s_num += numerators[idx]
            s_den += denominators[idx]
        ratio = s_num / s_den if s_den > 0 else 0.0
        resample_ratios.append(ratio)

    resample_ratios.sort()
    lo_idx = int((alpha / 2.0) * n_resamples)
    hi_idx = int((1.0 - alpha / 2.0) * n_resamples)
    hi_idx = min(hi_idx, n_resamples - 1)

    return point_estimate, float(resample_ratios[lo_idx]), float(resample_ratios[hi_idx])
