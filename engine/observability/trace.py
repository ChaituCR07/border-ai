"""Frame-level trace instrumentation and low-overhead trace sampling.

Each sampled frame records monotonic timestamps through its lifecycle:
  t_capture <= t_decoded <= t_pre <= t_inferred <= t_tracked <= t_events (<= t_rendered)

Used to derive:
- Processing latency distribution (capture -> tracking/events decided).
- Freshness / age at inference (capture -> pre-processing start; detects queueing).
- Annotated frame latency (capture -> MJPEG overlay encoded).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class FrameTrace:
    """Monotonic timestamps for a single sampled frame."""
    frame_id: int
    camera_id: str
    t_capture_ns: int
    t_decoded_ns: int
    t_pre_ns: int
    t_inferred_ns: int
    t_tracked_ns: int
    t_events_ns: int
    t_rendered_ns: Optional[int] = None

    @property
    def processing_latency_ms(self) -> float:
        """Wall-clock time from camera capture to events decided."""
        return max(0.0, (self.t_events_ns - self.t_capture_ns) / 1e6)

    @property
    def freshness_ms(self) -> float:
        """Age of frame at inference start (measures ingest queueing latency)."""
        return max(0.0, (self.t_pre_ns - self.t_capture_ns) / 1e6)

    @property
    def annotated_latency_ms(self) -> Optional[float]:
        """Latency to ready-to-stream annotated MJPEG frame."""
        if self.t_rendered_ns is None:
            return None
        return max(0.0, (self.t_rendered_ns - self.t_capture_ns) / 1e6)

    @property
    def is_monotonically_ordered(self) -> bool:
        """Verify temporal ordering across all pipeline stages."""
        ordered = (
            self.t_capture_ns <= self.t_decoded_ns <= self.t_pre_ns
            <= self.t_inferred_ns <= self.t_tracked_ns <= self.t_events_ns
        )
        if self.t_rendered_ns is not None:
            ordered = ordered and (self.t_events_ns <= self.t_rendered_ns)
        return ordered

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["processing_latency_ms"] = round(self.processing_latency_ms, 3)
        d["freshness_ms"] = round(self.freshness_ms, 3)
        if self.annotated_latency_ms is not None:
            d["annotated_latency_ms"] = round(self.annotated_latency_ms, 3)
        return d


class TraceSampler:
    """Deterministic rate-based frame trace sampler (default 1% rate)."""

    def __init__(self, sample_rate: float = 0.01, output_path: Optional[Path] = None):
        self.sample_rate = max(0.0, min(1.0, float(sample_rate)))
        self.output_path = output_path
        self._interval = max(1, int(round(1.0 / self.sample_rate))) if self.sample_rate > 0 else 0
        self.traces: List[FrameTrace] = []
        self._file_handle = None

        if self.output_path is not None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(self.output_path, "a", encoding="utf-8")

    def should_sample(self, frame_id: int) -> bool:
        if self._interval <= 0:
            return False
        return (frame_id % self._interval) == 0

    def record_trace(self, trace: FrameTrace) -> None:
        self.traces.append(trace)
        if self._file_handle is not None:
            self._file_handle.write(json.dumps(trace.to_dict()) + "\n")
            self._file_handle.flush()

    def close(self) -> None:
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

    def compute_summary(self) -> Dict[str, Any]:
        """Compute latency percentiles across all recorded sampled traces."""
        if not self.traces:
            return {
                "n_samples": 0,
                "processing_latency_p50_ms": 0.0,
                "processing_latency_p95_ms": 0.0,
                "processing_latency_p99_ms": 0.0,
                "freshness_p50_ms": 0.0,
                "freshness_p95_ms": 0.0,
            }

        proc = sorted(t.processing_latency_ms for t in self.traces)
        fresh = sorted(t.freshness_ms for t in self.traces)

        def pct(arr: Sequence[float], p: float) -> float:
            idx = int(round((len(arr) - 1) * (p / 100.0)))
            return float(arr[max(0, min(len(arr) - 1, idx))])

        return {
            "n_samples": len(self.traces),
            "processing_latency_p50_ms": round(pct(proc, 50.0), 3),
            "processing_latency_p95_ms": round(pct(proc, 95.0), 3),
            "processing_latency_p99_ms": round(pct(proc, 99.0), 3),
            "freshness_p50_ms": round(pct(fresh, 50.0), 3),
            "freshness_p95_ms": round(pct(fresh, 95.0), 3),
        }
