"""Data slice evaluation for operational environmental conditions and object sizes."""
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

from evaluation.datasets.base import DetSample, GtObject, PredObject
from evaluation.detection.metrics import evaluate_detection_class, get_size_bucket


@dataclass
class SliceMetricResult:
    slice_name: str
    slice_value: str
    num_samples: int
    num_gts: int
    precision: float
    recall: float
    f1: float
    ap50: float


def evaluate_attribute_slice(
    samples: Sequence[DetSample],
    predictions_per_sample: Sequence[Sequence[PredObject]],
    cls_name: str,
    slice_name: str,
    attribute_extractor: Callable[[DetSample], str],
    score_thresh: float = 0.35,
) -> List[SliceMetricResult]:
    """Partitions samples into slices and computes per-slice metrics."""
    buckets: Dict[str, List[int]] = {}
    for idx, s in enumerate(samples):
        val = attribute_extractor(s)
        buckets.setdefault(val, []).append(idx)

    results: List[SliceMetricResult] = []
    for val, indices in sorted(buckets.items()):
        slice_preds = [predictions_per_sample[i] for i in indices]
        slice_gts = [samples[i].gt for i in indices]
        total_gts = sum(1 for gts in slice_gts for g in gts if g.cls == cls_name and not g.ignore)

        if total_gts == 0:
            results.append(
                SliceMetricResult(
                    slice_name=slice_name,
                    slice_value=val,
                    num_samples=len(indices),
                    num_gts=0,
                    precision=0.0,
                    recall=0.0,
                    f1=0.0,
                    ap50=0.0,
                )
            )
            continue

        metrics = evaluate_detection_class(
            slice_preds, slice_gts, cls_name=cls_name, score_thresh=score_thresh
        )
        results.append(
            SliceMetricResult(
                slice_name=slice_name,
                slice_value=val,
                num_samples=len(indices),
                num_gts=total_gts,
                precision=metrics.precision,
                recall=metrics.recall,
                f1=metrics.f1,
                ap50=metrics.ap50,
            )
        )

    return results


def evaluate_size_slices(
    all_preds_per_img: List[Sequence[PredObject]],
    all_gts_per_img: List[Sequence[GtObject]],
    cls_name: str,
    score_thresh: float = 0.35,
) -> Dict[str, SliceMetricResult]:
    """Evaluates metrics filtered specifically by object size bucket (small, medium, large)."""
    results: Dict[str, SliceMetricResult] = {}

    for size_cat in ["small", "medium", "large"]:
        # Filter GTs and Preds to this size category
        filtered_gts: List[List[GtObject]] = []
        filtered_preds: List[List[PredObject]] = []

        for preds, gts in zip(all_preds_per_img, all_gts_per_img):
            f_gt = [g for g in gts if get_size_bucket(g.box.area) == size_cat]
            f_pred = [p for p in preds if get_size_bucket(p.box.area) == size_cat]
            filtered_gts.append(f_gt)
            filtered_preds.append(f_pred)

        num_gts = sum(1 for gts in filtered_gts for g in gts if g.cls == cls_name and not g.ignore)
        if num_gts == 0:
            results[size_cat] = SliceMetricResult(
                slice_name="object_size",
                slice_value=size_cat,
                num_samples=len(all_preds_per_img),
                num_gts=0,
                precision=0.0,
                recall=0.0,
                f1=0.0,
                ap50=0.0,
            )
        else:
            m = evaluate_detection_class(
                filtered_preds, filtered_gts, cls_name=cls_name, score_thresh=score_thresh
            )
            results[size_cat] = SliceMetricResult(
                slice_name="object_size",
                slice_value=size_cat,
                num_samples=len(all_preds_per_img),
                num_gts=num_gts,
                precision=m.precision,
                recall=m.recall,
                f1=m.f1,
                ap50=m.ap50,
            )

    return results
