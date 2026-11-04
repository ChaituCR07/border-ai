"""Confidence threshold sweep and operating point discovery."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from evaluation.datasets.base import GtObject, PredObject
from evaluation.detection.metrics import greedy_match_image


@dataclass
class SweepPoint:
    conf: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass
class SweepResult:
    cls_name: str
    optimal_conf: float
    optimal_f1: float
    optimal_precision: float
    optimal_recall: float
    curve: List[SweepPoint]


def sweep_confidence_thresholds(
    all_preds_per_img: List[Sequence[PredObject]],
    all_gts_per_img: List[Sequence[GtObject]],
    cls_name: str,
    thresholds: Optional[Sequence[float]] = None,
    iou_thresh: float = 0.5,
) -> SweepResult:
    """Evaluates metrics across confidence thresholds to determine the best operating point."""
    if thresholds is None:
        thresholds = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95

    curve: List[SweepPoint] = []
    best_f1 = -1.0
    best_conf = 0.35
    best_p = 0.0
    best_r = 0.0

    for conf in thresholds:
        tp = 0
        fp = 0
        fn = 0

        for preds, gts in zip(all_preds_per_img, all_gts_per_img):
            filt_preds = [p for p in preds if p.score >= conf]
            res = greedy_match_image(filt_preds, gts, iou_thresh=iou_thresh, target_class=cls_name)
            tp += res.tp
            fp += res.fp
            fn += res.fn

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        pt = SweepPoint(
            conf=conf,
            precision=prec,
            recall=rec,
            f1=f1,
            tp=tp,
            fp=fp,
            fn=fn,
        )
        curve.append(pt)

        if f1 > best_f1:
            best_f1 = f1
            best_conf = conf
            best_p = prec
            best_r = rec

    return SweepResult(
        cls_name=cls_name,
        optimal_conf=best_conf,
        optimal_f1=best_f1,
        optimal_precision=best_p,
        optimal_recall=best_r,
        curve=curve,
    )
