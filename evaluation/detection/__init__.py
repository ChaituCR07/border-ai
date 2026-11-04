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
]
