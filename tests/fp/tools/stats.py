"""Statistical estimators and interval calculations for false-positive evaluation.

Provides:
- Exact Garwood two-sided Poisson confidence intervals for alert rates.
- Rule of three upper bounds for zero-event exposure runs.
- Wilson score intervals for binomial proportions (precision, recall, lookalike collisions).
"""

from __future__ import annotations

import math
from typing import Tuple

try:
    from scipy.stats import chi2 as _scipy_chi2  # type: ignore
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def _regularized_gamma_p(s: float, x: float) -> float:
    """Regularized lower incomplete gamma function P(s, x) = gamma(s, x) / Gamma(s)."""
    if x <= 0.0 or s <= 0.0:
        return 0.0
    if x < s + 1.0:
        sum_val = 1.0 / s
        term = 1.0 / s
        for n in range(1, 200):
            term *= x / (s + n)
            sum_val += term
            if abs(term) < 1e-13:
                break
        return sum_val * math.exp(-x + s * math.log(x) - math.lgamma(s))
    else:
        # Lentz method continued fraction for upper incomplete gamma Q(s, x)
        b = x + 1.0 - s
        c = 1e30
        d = 1.0 / b if b != 0.0 else 1e-30
        h = d
        for i in range(1, 200):
            an = -i * (i - s)
            b += 2.0
            d = an * d + b
            if abs(d) < 1e-30:
                d = 1e-30
            c = b + an / c
            if abs(c) < 1e-30:
                c = 1e-30
            d = 1.0 / d
            delta = c * d
            h *= delta
            if abs(delta - 1.0) < 1e-13:
                break
        q = math.exp(-x + s * math.log(x) - math.lgamma(s)) * h
        return max(0.0, min(1.0, 1.0 - q))


def _chi2_cdf(df: float, x: float) -> float:
    """Cumulative distribution function of chi-squared with df degrees of freedom."""
    if x <= 0.0:
        return 0.0
    return _regularized_gamma_p(df / 2.0, x / 2.0)


def _chi2_ppf(p: float, df: float) -> float:
    """Percent point function (inverse CDF) of chi-squared distribution."""
    if _HAS_SCIPY:
        return float(_scipy_chi2.ppf(p, df))
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return float("inf")

    # Rational approximation for normal quantile
    t = math.sqrt(-2.0 * math.log(min(p, 1.0 - p)))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    z = t - ((c2 * t + c1) * t + c0) / (((d3 * t + d2) * t + d1) * t + 1.0)
    if p < 0.5:
        z = -z

    # Wilson-Hilferty transformation as starting seed
    term = 1.0 - 2.0 / (9.0 * df) + z * math.sqrt(2.0 / (9.0 * df))
    x = max(0.001, df * (term ** 3))

    # Newton-Raphson refinement
    for _ in range(60):
        cdf = _chi2_cdf(df, x)
        err = cdf - p
        if abs(err) < 1e-11:
            break
        s = df / 2.0
        log_pdf = (s - 1.0) * math.log(x) - x / 2.0 - s * math.log(2.0) - math.lgamma(s)
        pdf = math.exp(log_pdf)
        if pdf <= 1e-30:
            break
        dx = err / pdf
        x = max(0.00001, x - dx)
    return x


def poisson_ci(k: int, exposure_h: float, alpha: float = 0.05) -> Tuple[float, float]:
    """Exact (Garwood) two-sided confidence interval for a Poisson rate (events per hour).

    Args:
        k: Observed count of events (must be >= 0).
        exposure_h: Exposure denominator in camera-hours (must be > 0).
        alpha: Significance level (default 0.05 for 95% confidence).

    Returns:
        (rate_lo, rate_hi) in units of events per camera-hour.
    """
    if exposure_h <= 0.0:
        raise ValueError(f"exposure_h must be strictly positive, got {exposure_h}")
    if k < 0:
        raise ValueError(f"k must be non-negative, got {k}")

    if k == 0:
        lo = 0.0
        # When k = 0, chi2.ppf(1 - alpha/2, 2) / 2 == -ln(alpha / 2)
        hi = -math.log(alpha / 2.0) / exposure_h
        return lo, hi

    chi2_lo = _chi2_ppf(alpha / 2.0, 2 * k)
    chi2_hi = _chi2_ppf(1.0 - alpha / 2.0, 2 * (k + 1))
    return (chi2_lo / (2.0 * exposure_h)), (chi2_hi / (2.0 * exposure_h))


def rule_of_three(exposure_h: float) -> float:
    """One-sided 95% upper bound on Poisson rate when zero events are observed."""
    if exposure_h <= 0.0:
        raise ValueError(f"exposure_h must be strictly positive, got {exposure_h}")
    return 3.0 / exposure_h


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for binomial proportions.

    Args:
        k: Number of successes (0 <= k <= n).
        n: Total sample size.
        z: Normal distribution multiplier (1.96 for 95% confidence).

    Returns:
        (lower_bound, upper_bound) clamped to [0.0, 1.0].
    """
    if n == 0:
        return float("nan"), float("nan")
    if k < 0 or k > n:
        raise ValueError(f"k must be in [0, {n}], got {k}")

    p = k / float(n)
    denom = 1.0 + (z * z) / float(n)
    center = (p + (z * z) / (2.0 * float(n))) / denom
    margin = (z * math.sqrt((p * (1.0 - p)) / float(n) + (z * z) / (4.0 * float(n * n)))) / denom

    return max(0.0, center - margin), min(1.0, center + margin)
