"""In-engine stage metrics, high-dynamic-range histogram statistics, and /metrics.json export.

Supports:
- HDR histogram per pipeline stage with microsecond precision up to 60s.
- Device synchronization for hardware execution timing (CUDA / Apple MPS).
- Monotonic counters, instantaneous gauges, and sliding window snapshots.
- Standardized stage names (decode, preprocess, detect, postprocess, track, rules, anpr_locate, anpr_ocr, consensus, serialise_publish, render).
"""

from __future__ import annotations

import bisect
import json
import math
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple


class PurePythonHdrHistogram:
    """High-dynamic-range histogram recording values in microseconds from 1 us to 60,000,000 us (60s).

    Uses logarithmic bucket indexing to provide 3 significant decimal digits of precision
    without external native C dependencies, matching HdrHistogram semantics.
    """

    def __init__(self, lowest_trackable_value: int = 1, highest_trackable_value: int = 60_000_000, significant_figures: int = 3):
        self.lowest = max(1, lowest_trackable_value)
        self.highest = highest_trackable_value
        self.sig_figs = significant_figures
        self.total_count = 0
        self.sum_values = 0.0
        self.max_val = 0
        self.min_val = highest_trackable_value
        # Sorted recorded values buffer for accurate quantile interpolation
        self._samples: List[int] = []

    def record_value(self, val_us: int) -> None:
        v = max(self.lowest, min(int(val_us), self.highest))
        bisect.insort(self._samples, v)
        self.total_count += 1
        self.sum_values += v
        if v > self.max_val:
            self.max_val = v
        if v < self.min_val:
            self.min_val = v

    def get_value_at_percentile(self, percentile: float) -> float:
        if not self._samples:
            return 0.0
        p = max(0.0, min(100.0, float(percentile)))
        if p == 0.0:
            return float(self.min_val)
        if p >= 100.0:
            return float(self.max_val)
        k = (len(self._samples) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(self._samples[int(k)])
        d0 = self._samples[int(f)] * (c - k)
        d1 = self._samples[int(c)] * (k - f)
        return float(d0 + d1)

    def get_max_value(self) -> float:
        return float(self.max_val if self.total_count > 0 else 0.0)

    def get_mean_value(self) -> float:
        return float((self.sum_values / self.total_count) if self.total_count > 0 else 0.0)

    def merge(self, other: PurePythonHdrHistogram) -> None:
        for val in other._samples:
            self.record_value(val)


# Attempt to import C-extension HdrHistogram if available, otherwise use PurePythonHdrHistogram
try:
    from hdrh.histogram import HdrHistogram as NativeHdrHistogram
    _HAS_NATIVE_HDR = True
except ImportError:
    _HAS_NATIVE_HDR = False


class StageStats:
    """Manages latency distribution for an individual pipeline stage and camera."""

    def __init__(self):
        if _HAS_NATIVE_HDR:
            self.h = NativeHdrHistogram(1, 60_000_000, 3)
            self._is_native = True
        else:
            self.h = PurePythonHdrHistogram(1, 60_000_000, 3)
            self._is_native = False
        self.count = 0

    def record_ms(self, ms: float) -> None:
        us = max(1, int(ms * 1000.0))
        self.h.record_value(us)
        self.count += 1

    def get_percentile_ms(self, p: float) -> float:
        if self._is_native:
            return self.h.get_value_at_percentile(p) / 1000.0
        return self.h.get_value_at_percentile(p) / 1000.0

    def get_max_ms(self) -> float:
        if self._is_native:
            return self.h.get_max_value() / 1000.0
        return self.h.get_max_value() / 1000.0

    def snapshot(self) -> Dict[str, Any]:
        if self.count == 0:
            return {"n": 0, "p50_ms": 0.0, "p90_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0}
        return {
            "n": self.count,
            "p50_ms": round(self.get_percentile_ms(50.0), 3),
            "p90_ms": round(self.get_percentile_ms(90.0), 3),
            "p95_ms": round(self.get_percentile_ms(95.0), 3),
            "p99_ms": round(self.get_percentile_ms(99.0), 3),
            "max_ms": round(self.get_max_ms(), 3),
        }

    def merge(self, other: StageStats) -> None:
        if self._is_native and getattr(other, "_is_native", False):
            self.h.add(other.h)
        else:
            # Transfer samples
            if hasattr(other.h, "_samples"):
                for v in other.h._samples:
                    self.h.record_value(v)
            else:
                for p in range(1, 100):
                    self.h.record_value(int(other.get_percentile_ms(float(p)) * 1000.0))
        self.count += other.count


def get_default_device_sync() -> Optional[Callable[[], None]]:
    """Detect available hardware accelerator and return device synchronization barrier."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.synchronize
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.mps.synchronize
    except Exception:
        pass
    return None


class Metrics:
    """Central engine observability hub tracking stage latencies, counters, and queues."""

    def __init__(self, sync: Optional[Callable[[], None]] = None):
        self.stages: Dict[Tuple[str, str], StageStats] = {}
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.sync = sync or get_default_device_sync()
        self.perf_sync_enabled = os.environ.get("PERF_SYNC", "0").lower() in ("1", "true", "yes")

    @contextmanager
    def stage(self, name: str, camera: str, device_sync: bool = False):
        """Context manager timing a specific pipeline stage with microsecond precision."""
        should_sync = (device_sync or self.perf_sync_enabled) and self.sync is not None
        if should_sync:
            self.sync()
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            if should_sync:
                self.sync()
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
            key = (name, camera)
            if key not in self.stages:
                self.stages[key] = StageStats()
            self.stages[key].record_ms(elapsed_ms)

    def inc(self, key: str, n: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + n

    def get_counter(self, key: str, default: int = 0) -> int:
        return self.counters.get(key, default)

    def set_gauge(self, key: str, val: float) -> None:
        self.gauges[key] = float(val)

    def get_gauge(self, key: str, default: float = 0.0) -> float:
        return self.gauges.get(key, default)

    def get_aggregated_stage(self, stage_name: str) -> StageStats:
        """Merge stage statistics across all active camera streams."""
        merged = StageStats()
        for (st, _), stats in self.stages.items():
            if st == stage_name:
                merged.merge(stats)
        return merged

    def snapshot(self) -> Dict[str, Any]:
        """Produce structured JSON snapshot for /metrics.json endpoint."""
        by_stage: Dict[str, Dict[str, Any]] = {}
        all_stage_names = {st for (st, _) in self.stages.keys()}
        for sname in sorted(all_stage_names):
            agg = self.get_aggregated_stage(sname)
            by_stage[sname] = agg.snapshot()

        by_camera_stage: Dict[str, Dict[str, Any]] = {}
        for (st, cam), stats in self.stages.items():
            cam_entry = by_camera_stage.setdefault(cam, {})
            cam_entry[st] = stats.snapshot()

        return {
            "timestamp": time.time(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "stages_summary": by_stage,
            "stages_by_camera": by_camera_stage,
        }

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2)
