"""Windowed performance metrics aggregation, percentile calculation, and multi-repetition summarisation.

Aggregates:
- Windowed analytics FPS (from delta frames / window duration, not cumulative)
- Processing latency percentiles (p50, p90, p95, p99)
- Freshness latency percentiles
- Per-stage latency percentiles (merged across camera streams)
- Multi-repetition min, median, and max statistics
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class SingleRepetitionSummary:
    """Summary of a single benchmark repetition run."""
    repetition_index: int
    cameras: int
    duration_s: float
    analytics_fps_per_cam: float
    total_analytics_fps: float
    processing_latency_p50_ms: float
    processing_latency_p95_ms: float
    processing_latency_p99_ms: float
    freshness_p95_ms: float
    drop_rate: float
    gpu_util_percent: Optional[float] = None
    vram_mb: Optional[float] = None
    cpu_percent: float = 0.0
    ram_mb: float = 0.0
    alert_latency_p95_s: float = 0.0
    detections_per_frame: float = 0.0
    ocr_calls_per_sec: float = 0.0
    verdict: str = "VALID"
    verdict_reasons: List[str] = field(default_factory=list)
    stages_p50_ms: Dict[str, float] = field(default_factory=dict)
    stages_p95_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AggregatedBenchmarkSummary:
    """Aggregated results across multiple repetitions (min, median, max)."""
    spec_id: str
    cameras: int
    repetition_count: int
    verdict: str                               # VALID if all reps valid, else UNSTABLE/THROTTLED
    analytics_fps_median: float
    analytics_fps_min: float
    analytics_fps_max: float
    total_fps_median: float
    proc_lat_p50_median: float
    proc_lat_p95_median: float
    proc_lat_p99_median: float
    freshness_p95_median: float
    drop_rate_median: float
    gpu_util_median: str
    vram_mb_max: str
    cpu_percent_median: float
    ram_mb_max: float
    alert_latency_p95_median: float
    detections_per_frame: float
    ocr_calls_per_sec: float
    stages_breakdown_p50: Dict[str, float]
    stages_breakdown_p95: Dict[str, float]
    repetitions: List[SingleRepetitionSummary]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def aggregate_repetitions(spec_id: str, reps: Sequence[SingleRepetitionSummary]) -> AggregatedBenchmarkSummary:
    """Combine repetition runs into statistical min/median/max summary."""
    if not reps:
        raise ValueError("Cannot aggregate empty repetitions list")

    cameras = reps[0].cameras
    n = len(reps)
    fps_vals = [r.analytics_fps_per_cam for r in reps]
    tot_fps_vals = [r.total_analytics_fps for r in reps]
    p50_vals = [r.processing_latency_p50_ms for r in reps]
    p95_vals = [r.processing_latency_p95_ms for r in reps]
    p99_vals = [r.processing_latency_p99_ms for r in reps]
    fresh_vals = [r.freshness_p95_ms for r in reps]
    drop_vals = [r.drop_rate for r in reps]
    cpu_vals = [r.cpu_percent for r in reps]
    ram_vals = [r.ram_mb for r in reps]
    alert_vals = [r.alert_latency_p95_s for r in reps]

    valid_reps = [r for r in reps if r.verdict == "VALID"]
    overall_verdict = "VALID" if len(valid_reps) == n else ("THROTTLED" if any(r.verdict == "THROTTLED" for r in reps) else "UNSTABLE")

    gpu_utils = [r.gpu_util_percent for r in reps if r.gpu_util_percent is not None]
    vrams = [r.vram_mb for r in reps if r.vram_mb is not None]

    gpu_util_str = f"{median(gpu_utils):.1f}%" if gpu_utils else "n/a (mps/cpu)"
    vram_str = f"{max(vrams) / 1024.0:.2f} GB" if vrams else "n/a (unified)"

    # Aggregate stage breakdowns
    stages_p50: Dict[str, float] = {}
    stages_p95: Dict[str, float] = {}
    all_stages = set()
    for r in reps:
        all_stages.update(r.stages_p50_ms.keys())

    for st in all_stages:
        s50 = [r.stages_p50_ms[st] for r in reps if st in r.stages_p50_ms]
        s95 = [r.stages_p95_ms[st] for r in reps if st in r.stages_p95_ms]
        if s50:
            stages_p50[st] = round(median(s50), 2)
        if s95:
            stages_p95[st] = round(median(s95), 2)

    return AggregatedBenchmarkSummary(
        spec_id=spec_id,
        cameras=cameras,
        repetition_count=n,
        verdict=overall_verdict,
        analytics_fps_median=round(median(fps_vals), 1),
        analytics_fps_min=round(min(fps_vals), 1),
        analytics_fps_max=round(max(fps_vals), 1),
        total_fps_median=round(median(tot_fps_vals), 1),
        proc_lat_p50_median=round(median(p50_vals), 1),
        proc_lat_p95_median=round(median(p95_vals), 1),
        proc_lat_p99_median=round(median(p99_vals), 1),
        freshness_p95_median=round(median(fresh_vals), 1),
        drop_rate_median=round(median(drop_vals), 4),
        gpu_util_median=gpu_util_str,
        vram_mb_max=vram_str,
        cpu_percent_median=round(median(cpu_vals), 1),
        ram_mb_max=round(max(ram_vals), 1),
        alert_latency_p95_median=round(median(alert_vals), 2),
        detections_per_frame=round(median(r.detections_per_frame for r in reps), 1),
        ocr_calls_per_sec=round(median(r.ocr_calls_per_sec for r in reps), 2),
        stages_breakdown_p50=stages_p50,
        stages_breakdown_p95=stages_p95,
        repetitions=list(reps),
    )
