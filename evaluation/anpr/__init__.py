"""ANPR evaluation module: metrics, calibration, consensus, and error diagnostics."""
from evaluation.anpr.calibration import (
    confidently_wrong,
    coverage_accuracy,
    ece,
    rule_of_three_upper_bound,
    wilson_score_interval,
)
from evaluation.anpr.metrics import (
    align,
    confusion,
    corpus_metrics,
    plate_key,
    plate_norm,
    score_pair,
)

__all__ = [
    "plate_norm",
    "plate_key",
    "align",
    "score_pair",
    "corpus_metrics",
    "confusion",
    "ece",
    "coverage_accuracy",
    "confidently_wrong",
    "rule_of_three_upper_bound",
    "wilson_score_interval",
]
