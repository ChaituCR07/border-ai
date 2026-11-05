"""Stage-by-stage detection-to-plate funnel analysis.

Derives the monotone attribution funnel:
  Vehicles in set (N)
    -> vehicle detected (IoU >= 0.5)
    -> plate localized (IoU >= 0.5)
    -> OCR returns text
    -> exact match (single-frame best)
    -> passes validation
    -> consensus exact (multi-frame)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from evaluation.anpr.calibration import wilson_score_interval


@dataclass
class VehicleFunnelInput:
    """Per-vehicle stage outcome flags."""
    vehicle_id: str
    vehicle_detected: bool = False
    plate_localized: bool = False
    ocr_emitted: bool = False
    single_frame_exact: bool = False
    passed_validation: bool = False
    consensus_exact: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunnelStage:
    """A single stage in the monotonic pipeline funnel."""
    name: str
    count: int
    total_vehicles: int
    step_retention: float          # count / previous stage count
    overall_retention: float       # count / total_vehicles
    ci_95: Tuple[float, float]     # 95% Wilson CI for overall retention
    vehicle_ids: Set[str] = field(default_factory=set)


@dataclass
class FunnelReport:
    """Consolidated funnel attribution report."""
    total_vehicles: int
    stages: List[FunnelStage]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_vehicles": self.total_vehicles,
            "stages": [
                {
                    "name": s.name,
                    "count": s.count,
                    "step_retention": round(s.step_retention, 4),
                    "overall_retention": round(s.overall_retention, 4),
                    "ci_95": (round(s.ci_95[0], 4), round(s.ci_95[1], 4)),
                }
                for s in self.stages
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            "| Stage | Count | Step Retention | Cumulative Retention | 95% CI |",
            "|---|---|---|---|---|",
        ]
        for s in self.stages:
            ci_str = f"[{s.ci_95[0]:.1%}, {s.ci_95[1]:.1%}]"
            step_str = f"{s.step_retention:.1%}" if s.step_retention is not None else "-"
            lines.append(
                f"| **{s.name}** | {s.count} | {step_str} | {s.overall_retention:.1%} | {ci_str} |"
            )
        return "\n".join(lines)


def build_pipeline_funnel(records: List[VehicleFunnelInput]) -> FunnelReport:
    """Constructs a monotone funnel from vehicle records.

    Monotonicity invariant is guaranteed: each successive stage requires
    that all prerequisite stages succeeded.
    """
    total = len(records)
    if total == 0:
        return FunnelReport(0, [])

    # Stage 0: Ground truth vehicles
    v_all = {r.vehicle_id for r in records}

    # Stage 1: Vehicle detected
    v_detected = {r.vehicle_id for r in records if r.vehicle_id in v_all and r.vehicle_detected}

    # Stage 2: Plate localized given vehicle detected
    v_localized = {r.vehicle_id for r in records if r.vehicle_id in v_detected and r.plate_localized}

    # Stage 3: OCR returned text given plate localized
    v_ocr = {r.vehicle_id for r in records if r.vehicle_id in v_localized and r.ocr_emitted}

    # Stage 4: Single frame exact match given OCR text
    v_single_exact = {r.vehicle_id for r in records if r.vehicle_id in v_ocr and r.single_frame_exact}

    # Stage 5: Passes format validation given exact match
    v_validated = {r.vehicle_id for r in records if r.vehicle_id in v_single_exact and r.passed_validation}

    # Stage 6: Consensus exact (recovers or confirms across multiple frames)
    # Note: multi-frame consensus can also recover vehicles where single frame was near-miss
    v_consensus = {r.vehicle_id for r in records if r.vehicle_id in v_ocr and r.consensus_exact}

    stages_def = [
        ("Vehicles in evaluation set", v_all),
        ("Vehicle detected (IoU >= 0.5)", v_detected),
        ("Plate localized (IoU >= 0.5)", v_localized),
        ("OCR returned text", v_ocr),
        ("Exact match (single frame)", v_single_exact),
        ("Passes validation", v_validated),
        ("Consensus exact (multi-frame)", v_consensus),
    ]

    stages: List[FunnelStage] = []
    prev_count = total
    for name, v_set in stages_def:
        cnt = len(v_set)
        step_ret = cnt / prev_count if prev_count > 0 else 0.0
        overall_ret = cnt / total if total > 0 else 0.0
        ci = wilson_score_interval(cnt, total)
        stages.append(
            FunnelStage(
                name=name,
                count=cnt,
                total_vehicles=total,
                step_retention=step_ret,
                overall_retention=overall_ret,
                ci_95=ci,
                vehicle_ids=v_set,
            )
        )
        prev_count = cnt

    return FunnelReport(total_vehicles=total, stages=stages)
