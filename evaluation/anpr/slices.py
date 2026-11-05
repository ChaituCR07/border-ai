"""Environmental and geometry slice analysis for ANPR evaluation.

Evaluates performance across:
1. Plate height (px): <20px, 20-30px, 30-50px, 50-80px, >80px
   -> Derives the minimum plate height for >= 90% exact accuracy.
2. Viewing angle: frontal, oblique, steep.
3. Lighting / Weather: day, night, rain, glare, blur.
4. Vehicle type: car, motorcycle (two-wheeler), bus, truck.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from evaluation.anpr.calibration import wilson_score_interval
from evaluation.anpr.datasets.india_anpr import AnprSample
from evaluation.anpr.metrics import corpus_metrics, score_pair, plate_key
from evaluation.anpr.predict import PredictionResult


HEIGHT_BUCKET_ORDER = ["<20px", "20-30px", "30-50px", "50-80px", ">80px"]


@dataclass
class SliceBucket:
    """Evaluation summary for a specific operational slice."""
    slice_type: str
    bucket_name: str
    sample_count: int
    vehicle_count: int
    read_rate: float
    exact_accuracy: float
    lookalike_accuracy: float
    char_accuracy: float
    ci_exact: Tuple[float, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SliceAnalysisReport:
    """Collection of slice evaluations with operational threshold derivations."""
    slices: Dict[str, List[SliceBucket]]

    def minimum_height_for_target_accuracy(self, target_accuracy: float = 0.90) -> Optional[str]:
        """Derive minimum plate height bucket achieving >= target_accuracy."""
        buckets = self.slices.get("plate_height", [])
        for b in buckets:
            if b.exact_accuracy >= target_accuracy and b.sample_count >= 1:
                return b.bucket_name
        return None

    def unusable_height_bucket(self, failure_threshold: float = 0.60) -> Optional[str]:
        """Derive plate height bucket considered unusable (< failure_threshold accuracy)."""
        buckets = self.slices.get("plate_height", [])
        for b in buckets:
            if b.exact_accuracy < failure_threshold and b.sample_count >= 1:
                return b.bucket_name
        return None

    def to_markdown(self) -> str:
        lines = []
        for slice_type, buckets in self.slices.items():
            lines.append(f"### Operational Slice: {slice_type.replace('_', ' ').title()}")
            lines.append("")
            lines.append("| Bucket | Samples | Vehicles | Read Rate | Exact Acc | 95% CI | Look-alike Acc | Char Acc |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for b in buckets:
                ci_str = f"[{b.ci_exact[0]:.1%}, {b.ci_exact[1]:.1%}]"
                lines.append(
                    f"| **{b.bucket_name}** | {b.sample_count} | {b.vehicle_count} | "
                    f"{b.read_rate:.1%} | {b.exact_accuracy:.1%} | {ci_str} | "
                    f"{b.lookalike_accuracy:.1%} | {b.char_accuracy:.1%} |"
                )
            lines.append("")
        return "\n".join(lines)


def _compute_bucket_metrics(
    slice_type: str,
    bucket_name: str,
    items: List[Tuple[AnprSample, PredictionResult]],
) -> SliceBucket:
    total_samples = len(items)
    if total_samples == 0:
        return SliceBucket(
            slice_type=slice_type,
            bucket_name=bucket_name,
            sample_count=0,
            vehicle_count=0,
            read_rate=0.0,
            exact_accuracy=0.0,
            lookalike_accuracy=0.0,
            char_accuracy=0.0,
            ci_exact=(0.0, 0.0),
        )

    unique_vehicles = len({s.vehicle_id for s, _ in items})
    pairs = [score_pair(s.plate_norm, r.pred_text, plate_key) for s, r in items]
    corpus = corpus_metrics(pairs)

    exact_successes = sum(p["exact"] for p in pairs)
    ci = wilson_score_interval(exact_successes, total_samples)

    return SliceBucket(
        slice_type=slice_type,
        bucket_name=bucket_name,
        sample_count=total_samples,
        vehicle_count=unique_vehicles,
        read_rate=corpus["read_rate"],
        exact_accuracy=corpus["plate_exact"],
        lookalike_accuracy=corpus["lookalike_equiv"],
        char_accuracy=corpus["char_accuracy"],
        ci_exact=ci,
    )


def analyze_slices(
    samples: List[AnprSample],
    predictions: List[PredictionResult],
) -> SliceAnalysisReport:
    """Partition samples and predictions into environmental and geometry slices."""
    pred_map = {p.sample_id: p for p in predictions}
    matched_pairs: List[Tuple[AnprSample, PredictionResult]] = []
    for s in samples:
        if s.sample_id in pred_map:
            matched_pairs.append((s, pred_map[s.sample_id]))

    # Group by plate height
    height_groups: Dict[str, List[Tuple[AnprSample, PredictionResult]]] = defaultdict(list)
    for s, p in matched_pairs:
        bucket = s.plate_height_bucket
        height_groups[bucket].append((s, p))

    height_buckets = [
        _compute_bucket_metrics("plate_height", b_name, height_groups.get(b_name, []))
        for b_name in HEIGHT_BUCKET_ORDER
        if b_name in height_groups or len(samples) == 0
    ]

    # Group by viewing angle
    angle_groups: Dict[str, List[Tuple[AnprSample, PredictionResult]]] = defaultdict(list)
    for s, p in matched_pairs:
        cond = s.condition if isinstance(s.condition, dict) else {}
        angle = cond.get("angle", getattr(s, "angle_bucket", "frontal"))
        angle_groups[angle].append((s, p))

    angle_buckets = [
        _compute_bucket_metrics("viewing_angle", a_name, angle_groups[a_name])
        for a_name in sorted(angle_groups.keys())
    ]

    # Group by lighting / environment
    light_groups: Dict[str, List[Tuple[AnprSample, PredictionResult]]] = defaultdict(list)
    for s, p in matched_pairs:
        cond = s.condition if isinstance(s.condition, dict) else {}
        lighting = cond.get("lighting", "day")
        light_groups[lighting].append((s, p))

    light_buckets = [
        _compute_bucket_metrics("lighting_condition", l_name, light_groups[l_name])
        for l_name in sorted(light_groups.keys())
    ]

    # Group by vehicle type
    type_groups: Dict[str, List[Tuple[AnprSample, PredictionResult]]] = defaultdict(list)
    for s, p in matched_pairs:
        v_type = s.vehicle_type or "car"
        type_groups[v_type].append((s, p))

    type_buckets = [
        _compute_bucket_metrics("vehicle_type", t_name, type_groups[t_name])
        for t_name in sorted(type_groups.keys())
    ]

    return SliceAnalysisReport(
        slices={
            "plate_height": height_buckets,
            "viewing_angle": angle_buckets,
            "lighting_condition": light_buckets,
            "vehicle_type": type_buckets,
        }
    )
