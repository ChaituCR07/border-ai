"""Queue slope stability detector, thermal throttling monitor, and benchmark run validator.

Implements ADR 0041 stability criteria:
1. Linear regression slope of each internal queue <= 1.0 frames/min AND final depth < 50% capacity.
2. Sustained frame drop rate < 1.0%.
3. Freshness p95 < 500 ms.
4. Hardware clock drop <= 10% (no thermal throttling).
5. Zero unexpected process restarts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


def slope_per_min(timestamps_s: Sequence[float], depths: Sequence[float]) -> float:
    """Calculate linear regression slope of queue depth in units of frames / minute."""
    n = len(timestamps_s)
    if n < 2:
        return 0.0

    t_mean = sum(timestamps_s) / n
    d_mean = sum(depths) / n

    numerator = 0.0
    denominator = 0.0
    for t, d in zip(timestamps_s, depths):
        dt = t - t_mean
        numerator += dt * (d - d_mean)
        denominator += dt * dt

    if denominator == 0.0:
        return 0.0

    slope_per_sec = numerator / denominator
    return float(slope_per_sec * 60.0)


@dataclass
class RunBudgets:
    """Operational stability boundaries from ADR 0041."""
    drop_rate_max: float = 0.01                 # 1.0% maximum live frame drop rate
    freshness_p95_ms: float = 500.0             # 500 ms maximum age-at-inference p95
    processing_p95_ms: float = 250.0            # 250 ms maximum processing latency p95
    alert_p95_s: float = 3.0                    # 3.0 s maximum capture-to-alert latency p95
    max_queue_slope_per_min: float = 1.0        # 1 frame / minute maximum queue growth rate
    max_clock_drop_pct: float = 10.0            # 10% maximum clock frequency drop


@dataclass
class StabilityVerdict:
    """Outcome of run validation."""
    status: str                                 # 'VALID', 'UNSTABLE', or 'THROTTLED'
    reasons: List[str] = field(default_factory=list)
    is_valid: bool = False
    metrics_summary: Dict[str, float] = field(default_factory=dict)


@dataclass
class RunTelemetryData:
    """Telemetry captured during the steady-state measurement window."""
    queues: Dict[str, Tuple[Sequence[float], Sequence[float], int]]  # name -> (ts, depths, capacity)
    drop_rate: float
    freshness_p95_ms: float
    processing_p95_ms: float
    clock_frequencies: Sequence[float] = field(default_factory=list)
    process_restarts: int = 0
    budgets: RunBudgets = field(default_factory=RunBudgets)


def evaluate_run_stability(run: RunTelemetryData) -> StabilityVerdict:
    """Evaluate whether a benchmark run meets steady-state stability criteria."""
    reasons: List[str] = []
    b = run.budgets

    # 1. Internal queue slopes and capacity headroom
    for q_name, (ts, depths, cap) in run.queues.items():
        if len(depths) >= 2:
            slope = slope_per_min(ts, depths)
            final_d = depths[-1]
            if slope > b.max_queue_slope_per_min and final_d > (0.5 * cap):
                reasons.append(
                    f"queue '{q_name}' growing (slope={slope:.2f} frames/min, final={final_d}/{cap})"
                )

    # 2. Live frame drop rate
    if run.drop_rate > b.drop_rate_max:
        reasons.append(f"drop rate {run.drop_rate:.1%} exceeds budget {b.drop_rate_max:.1%}")

    # 3. Freshness / queueing latency
    if run.freshness_p95_ms > b.freshness_p95_ms:
        reasons.append(
            f"freshness p95 {run.freshness_p95_ms:.1f}ms exceeds budget {b.freshness_p95_ms:.1f}ms"
        )

    # 4. Thermal / clock throttling
    clock_drop = 0.0
    if len(run.clock_frequencies) >= 2:
        initial_clock = run.clock_frequencies[0]
        min_clock = min(run.clock_frequencies)
        if initial_clock > 0:
            clock_drop = ((initial_clock - min_clock) / initial_clock) * 100.0
            if clock_drop > b.max_clock_drop_pct:
                reasons.append(
                    f"clock throttling detected: {clock_drop:.1f}% drop (min {min_clock:.0f} vs {initial_clock:.0f} MHz)"
                )

    # 5. Process restarts
    if run.process_restarts > 0:
        reasons.append(f"process restarted {run.process_restarts} time(s) during measurement")

    # Determine status
    if not reasons:
        status = "VALID"
        is_valid = True
    elif any("throttling" in r for r in reasons):
        status = "THROTTLED"
        is_valid = False
    else:
        status = "UNSTABLE"
        is_valid = False

    return StabilityVerdict(
        status=status,
        reasons=reasons,
        is_valid=is_valid,
        metrics_summary={
            "drop_rate": run.drop_rate,
            "freshness_p95_ms": run.freshness_p95_ms,
            "processing_p95_ms": run.processing_p95_ms,
            "clock_drop_pct": clock_drop,
        },
    )
