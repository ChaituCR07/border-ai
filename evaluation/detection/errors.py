"""Detection error taxonomy and diagnostic categorization."""
from enum import Enum
from typing import Dict, List, Sequence

from evaluation.datasets.base import Box, GtObject, PredObject
from evaluation.detection.metrics import compute_iou


class ErrorType(str, Enum):
    CORRECT = "correct"
    LOCALIZATION = "localization_error"
    CLASSIFICATION = "classification_error"
    DUPLICATE = "duplicate_detection"
    BACKGROUND = "background_false_positive"
    MISSED_GT = "missed_ground_truth"


def categorize_detections(
    predictions: Sequence[PredObject],
    ground_truths: Sequence[GtObject],
    iou_thresh: float = 0.5,
    min_loc_iou: float = 0.1,
) -> Dict[ErrorType, int]:
    """Classifies detections into actionable error categories."""
    preds = sorted(predictions, key=lambda p: p.score, reverse=True)
    matched_gt_indices = set()
    counts = {e: 0 for e in ErrorType}

    for pred in preds:
        best_same_cls_iou = 0.0
        best_same_cls_idx = -1
        best_diff_cls_iou = 0.0

        for idx, gt in enumerate(ground_truths):
            iou = compute_iou(pred.box, gt.box)
            if gt.cls == pred.cls:
                if iou > best_same_cls_iou:
                    best_same_cls_iou = iou
                    best_same_cls_idx = idx
            else:
                if iou > best_diff_cls_iou:
                    best_diff_cls_iou = iou

        if best_same_cls_iou >= iou_thresh:
            if best_same_cls_idx in matched_gt_indices:
                counts[ErrorType.DUPLICATE] += 1
            else:
                counts[ErrorType.CORRECT] += 1
                matched_gt_indices.add(best_same_cls_idx)
        elif best_diff_cls_iou >= iou_thresh:
            counts[ErrorType.CLASSIFICATION] += 1
        elif best_same_cls_iou >= min_loc_iou:
            counts[ErrorType.LOCALIZATION] += 1
        else:
            counts[ErrorType.BACKGROUND] += 1

    # Count missed GTs (non-ignored)
    for idx, gt in enumerate(ground_truths):
        if not gt.ignore and idx not in matched_gt_indices:
            counts[ErrorType.MISSED_GT] += 1

    return counts
