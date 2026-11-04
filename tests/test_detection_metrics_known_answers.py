"""Known-answer tests for detection evaluation metrics and error taxonomy."""
from evaluation.datasets.base import Box, GtObject, PredObject
from evaluation.detection.errors import ErrorType, categorize_detections
from evaluation.detection.metrics import (
    compute_ap,
    compute_footpoint_error,
    compute_iou,
    evaluate_detection_class,
    get_size_bucket,
    greedy_match_image,
)


def test_compute_iou_known_values() -> None:
    # Identical boxes -> 1.0
    b1 = Box(x=0, y=0, w=100, h=100)
    b2 = Box(x=0, y=0, w=100, h=100)
    assert compute_iou(b1, b2) == 1.0

    # Non-overlapping boxes -> 0.0
    b3 = Box(x=200, y=200, w=50, h=50)
    assert compute_iou(b1, b3) == 0.0

    # 50% overlap horizontally:
    # b1: 0..100, b4: 50..150. Inter = 50 * 100 = 5000. Union = 10000 + 10000 - 5000 = 15000.
    # IoU = 5000 / 15000 = 1/3
    b4 = Box(x=50, y=0, w=100, h=100)
    assert abs(compute_iou(b1, b4) - (1.0 / 3.0)) < 1e-6


def test_footpoint_error_known_values() -> None:
    # b1 foot point: (50, 100)
    b1 = Box(x=0, y=0, w=100, h=100)
    # b2 foot point: (60, 100) -> dx = 10, dy = 0 -> distance = 10.0
    b2 = Box(x=10, y=0, w=100, h=100)
    assert abs(compute_footpoint_error(b1, b2) - 10.0) < 1e-6

    # b3 foot point: (50, 110) -> dx = 0, dy = 10 -> distance = 10.0
    b3 = Box(x=0, y=10, w=100, h=100)
    assert abs(compute_footpoint_error(b1, b3) - 10.0) < 1e-6


def test_greedy_match_iou_boundary_and_duplicates() -> None:
    gt = [GtObject(cls="person", box=Box(0, 0, 100, 100))]

    # Pred 1: IoU 1.0, score 0.9 -> TP
    # Pred 2: IoU 1.0, score 0.8 -> Duplicate FP
    preds = [
        PredObject(cls="person", score=0.9, box=Box(0, 0, 100, 100)),
        PredObject(cls="person", score=0.8, box=Box(0, 0, 100, 100)),
    ]
    res = greedy_match_image(preds, gt, iou_thresh=0.5)
    assert res.tp == 1
    assert res.fp == 1
    assert res.fn == 0


def test_greedy_match_ignore_region() -> None:
    gt = [
        GtObject(cls="person", box=Box(0, 0, 100, 100), ignore=True),
        GtObject(cls="person", box=Box(200, 200, 50, 50), ignore=False),
    ]
    # Pred overlapping the ignored GT
    preds = [PredObject(cls="person", score=0.9, box=Box(0, 0, 100, 100))]
    res = greedy_match_image(preds, gt, iou_thresh=0.5)
    assert res.tp == 0
    assert res.fp == 0
    assert res.ignored_preds == 1
    assert res.fn == 1  # The non-ignored GT at (200, 200) is unmatched


def test_evaluate_detection_class_perfect_and_empty() -> None:
    # 1. Perfect detections across 2 images
    img1_gt = [GtObject("person", Box(10, 10, 50, 100))]
    img1_pred = [PredObject("person", 0.95, Box(10, 10, 50, 100))]

    img2_gt = [GtObject("person", Box(20, 20, 40, 80))]
    img2_pred = [PredObject("person", 0.90, Box(20, 20, 40, 80))]

    metrics = evaluate_detection_class([img1_pred, img2_pred], [img1_gt, img2_gt], "person", score_thresh=0.35)
    assert metrics.tp == 2
    assert metrics.fp == 0
    assert metrics.fn == 0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert abs(metrics.ap50 - 1.0) < 1e-4
    assert abs(metrics.map_50_95 - 1.0) < 1e-4
    assert metrics.mean_footpoint_error_px == 0.0

    # 2. Empty predictions
    empty_metrics = evaluate_detection_class([[], []], [img1_gt, img2_gt], "person", score_thresh=0.35)
    assert empty_metrics.tp == 0
    assert empty_metrics.fp == 0
    assert empty_metrics.fn == 2
    assert empty_metrics.precision == 0.0
    assert empty_metrics.recall == 0.0
    assert empty_metrics.f1 == 0.0
    assert empty_metrics.ap50 == 0.0


def test_error_taxonomy_categorization() -> None:
    gt_list = [
        GtObject("person", Box(0, 0, 100, 100)),       # Matched by p1
        GtObject("car", Box(300, 300, 80, 80)),        # Matched by p3 as classification error
        GtObject("person", Box(500, 500, 60, 60)),     # Unmatched -> MISSED_GT
    ]

    preds = [
        PredObject("person", 0.95, Box(0, 0, 100, 100)),     # Correct
        PredObject("person", 0.90, Box(0, 0, 100, 100)),     # Duplicate
        PredObject("person", 0.85, Box(300, 300, 80, 80)),   # Classification error (pred person, gt car)
        PredObject("person", 0.80, Box(0, 0, 100, 35)),      # Localization error (IoU 0.35 with GT 0)
        PredObject("person", 0.70, Box(900, 900, 40, 40)),   # Background
    ]

    cats = categorize_detections(preds, gt_list, iou_thresh=0.5, min_loc_iou=0.1)
    assert cats[ErrorType.CORRECT] == 1
    assert cats[ErrorType.DUPLICATE] == 1
    assert cats[ErrorType.CLASSIFICATION] == 1
    assert cats[ErrorType.LOCALIZATION] == 1
    assert cats[ErrorType.BACKGROUND] == 1
    assert cats[ErrorType.MISSED_GT] == 2


def test_size_buckets() -> None:
    assert get_size_bucket(500.0) == "small"        # < 1024
    assert get_size_bucket(2000.0) == "medium"      # 1024..9216
    assert get_size_bucket(15000.0) == "large"      # >= 9216
