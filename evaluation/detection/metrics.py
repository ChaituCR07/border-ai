"""Detection evaluation metrics, greedy matcher, mAP, and operating point evaluation."""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from evaluation.datasets.base import Box, GtObject, PredObject


def compute_iou(box1: Box, box2: Box) -> float:
    """Computes Intersection over Union (IoU) of two bounding boxes."""
    x1 = max(box1.x, box2.x)
    y1 = max(box1.y, box2.y)
    x2 = min(box1.x2, box2.x2)
    y2 = min(box1.y2, box2.y2)

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    union_area = box1.area + box2.area - inter_area
    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def compute_footpoint_error(box1: Box, box2: Box) -> float:
    """Computes Euclidean distance in pixels between the bottom-center foot points."""
    fx1, fy1 = box1.foot_point
    fx2, fy2 = box2.foot_point
    return math.hypot(fx1 - fx2, fy1 - fy2)


def get_size_bucket(area: float) -> str:
    """Returns COCO size bucket: 'small' (<32^2), 'medium' (32^2..96^2), or 'large' (>=96^2)."""
    if area < 32.0 * 32.0:
        return "small"
    if area < 96.0 * 96.0:
        return "medium"
    return "large"


@dataclass
class MatchResult:
    """Per-image matching results for a single IoU threshold."""
    tp: int = 0
    fp: int = 0
    fn: int = 0
    ignored_preds: int = 0
    # List of (is_tp, is_fp, score, foot_point_err, pred_box, matched_gt)
    pred_matches: List[Tuple[bool, bool, float, Optional[float], PredObject, Optional[GtObject]]] = field(default_factory=list)


def greedy_match_image(
    predictions: Sequence[PredObject],
    ground_truths: Sequence[GtObject],
    iou_thresh: float = 0.5,
    target_class: Optional[str] = None,
) -> MatchResult:
    """Matches predictions to ground truths using greedy highest-IoU matching."""
    preds = [p for p in predictions if (target_class is None or p.cls == target_class)]
    preds = sorted(preds, key=lambda p: p.score, reverse=True)

    gts = [g for g in ground_truths if (target_class is None or g.cls == target_class)]
    matched_gt_indices: set = set()
    result = MatchResult()

    for pred in preds:
        best_iou = 0.0
        best_gt_idx = -1

        for idx, gt in enumerate(gts):
            iou = compute_iou(pred.box, gt.box)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = idx

        if best_iou >= iou_thresh and best_gt_idx >= 0:
            matched_gt = gts[best_gt_idx]
            if matched_gt.ignore:
                # Matched an ignored ground truth -> neither TP nor FP
                result.ignored_preds += 1
                result.pred_matches.append((False, False, pred.score, None, pred, matched_gt))
            elif best_gt_idx in matched_gt_indices:
                # Duplicate detection on already matched ground truth
                result.fp += 1
                result.pred_matches.append((False, True, pred.score, None, pred, matched_gt))
            else:
                # Valid True Positive
                result.tp += 1
                matched_gt_indices.add(best_gt_idx)
                fp_err = compute_footpoint_error(pred.box, matched_gt.box)
                result.pred_matches.append((True, False, pred.score, fp_err, pred, matched_gt))
        else:
            # Check if it overlaps any ignored GT above threshold before counting as FP
            overlap_ignored = False
            for gt in gts:
                if gt.ignore and compute_iou(pred.box, gt.box) >= iou_thresh:
                    overlap_ignored = True
                    break

            if overlap_ignored:
                result.ignored_preds += 1
                result.pred_matches.append((False, False, pred.score, None, pred, None))
            else:
                result.fp += 1
                result.pred_matches.append((False, True, pred.score, None, pred, None))

    # Any non-ignored ground truth not matched is a False Negative
    for idx, gt in enumerate(gts):
        if not gt.ignore and idx not in matched_gt_indices:
            result.fn += 1

    return result


def compute_ap(recalls: Sequence[float], precisions: Sequence[float]) -> float:
    """Computes Area Under PR Curve using 101-point COCO interpolation."""
    if not recalls or not precisions:
        return 0.0

    # Ensure endpoints
    mrec = [0.0] + list(recalls) + [1.0]
    mpre = [0.0] + list(precisions) + [0.0]

    # Monotonic decreasing envelope for precision
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])

    # 101-point sampling (COCO metric)
    recall_levels = [i / 100.0 for i in range(101)]
    ap = 0.0
    for r in recall_levels:
        # Find max precision for recall >= r
        prec_at_r = 0.0
        for rec_val, prec_val in zip(mrec, mpre):
            if rec_val >= r:
                prec_at_r = max(prec_at_r, prec_val)
        ap += prec_at_r

    return ap / 101.0


@dataclass
class ClassMetrics:
    cls_name: str
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    mean_footpoint_error_px: float
    ap50: float
    ap75: float
    map_50_95: float


def evaluate_detection_class(
    all_preds_per_img: List[Sequence[PredObject]],
    all_gts_per_img: List[Sequence[GtObject]],
    cls_name: str,
    score_thresh: float = 0.35,
) -> ClassMetrics:
    """Computes comprehensive evaluation metrics for a single class."""
    # Count total non-ignored GTs
    total_gts = sum(1 for gts in all_gts_per_img for g in gts if g.cls == cls_name and not g.ignore)

    # 1. Operating point evaluation at score_thresh (IoU = 0.50)
    op_tp = 0
    op_fp = 0
    op_fn = 0
    footpoint_errors: List[float] = []

    for preds, gts in zip(all_preds_per_img, all_gts_per_img):
        filt_preds = [p for p in preds if p.score >= score_thresh]
        res = greedy_match_image(filt_preds, gts, iou_thresh=0.50, target_class=cls_name)
        op_tp += res.tp
        op_fp += res.fp
        op_fn += res.fn
        for is_tp, _, _, fp_err, _, _ in res.pred_matches:
            if is_tp and fp_err is not None:
                footpoint_errors.append(fp_err)

    prec = op_tp / (op_tp + op_fp) if (op_tp + op_fp) > 0 else 0.0
    rec = op_tp / (op_tp + op_fn) if (op_tp + op_fn) > 0 else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    mean_fp_err = sum(footpoint_errors) / len(footpoint_errors) if footpoint_errors else 0.0

    # 2. Compute AP across IoU thresholds (0.50:0.05:0.95)
    def compute_ap_at_iou(iou_th: float) -> float:
        all_eval_items: List[Tuple[float, bool, bool]] = []  # (score, is_tp, is_fp)
        for preds, gts in zip(all_preds_per_img, all_gts_per_img):
            res = greedy_match_image(preds, gts, iou_thresh=iou_th, target_class=cls_name)
            for is_tp, is_fp, sc, _, _, _ in res.pred_matches:
                if is_tp or is_fp:
                    all_eval_items.append((sc, is_tp, is_fp))

        if not all_eval_items or total_gts == 0:
            return 0.0

        all_eval_items.sort(key=lambda x: x[0], reverse=True)
        acc_tp = 0
        acc_fp = 0
        precisions = []
        recalls = []

        for sc, is_tp, is_fp in all_eval_items:
            if is_tp:
                acc_tp += 1
            elif is_fp:
                acc_fp += 1
            p = acc_tp / (acc_tp + acc_fp)
            r = acc_tp / total_gts
            precisions.append(p)
            recalls.append(r)

        return compute_ap(recalls, precisions)

    ap50 = compute_ap_at_iou(0.50)
    ap75 = compute_ap_at_iou(0.75)
    all_aps = [compute_ap_at_iou(round(th, 2)) for th in [0.50 + 0.05 * i for i in range(10)]]
    map_50_95 = sum(all_aps) / len(all_aps)

    return ClassMetrics(
        cls_name=cls_name,
        tp=op_tp,
        fp=op_fp,
        fn=op_fn,
        precision=prec,
        recall=rec,
        f1=f1,
        mean_footpoint_error_px=mean_fp_err,
        ap50=ap50,
        ap75=ap75,
        map_50_95=map_50_95,
    )
