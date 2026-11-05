"""ANPR evaluation module: metrics, calibration, consensus, and error diagnostics."""
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
]
