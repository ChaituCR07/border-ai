"""Detection evaluation package."""
from evaluation.detection.errors import ErrorType, categorize_detections
from evaluation.detection.metrics import (
    ClassMetrics,
    MatchResult,
    compute_ap,
    compute_footpoint_error,
    compute_iou,
    evaluate_detection_class,
    get_size_bucket,
    greedy_match_image,
)
from evaluation.detection.predict import EvaluationDetector
from evaluation.detection.slices import (
    SliceMetricResult,
    evaluate_attribute_slice,
    evaluate_size_slices,
)
from evaluation.detection.sweep import SweepPoint, SweepResult, sweep_confidence_thresholds

__all__ = [
    "compute_iou",
    "compute_footpoint_error",
    "get_size_bucket",
    "MatchResult",
    "greedy_match_image",
    "compute_ap",
    "ClassMetrics",
    "evaluate_detection_class",
    "ErrorType",
    "categorize_detections",
    "EvaluationDetector",
    "SweepPoint",
    "SweepResult",
    "sweep_confidence_thresholds",
    "SliceMetricResult",
    "evaluate_attribute_slice",
    "evaluate_size_slices",
]
