import threading
from collections import deque
from typing import Dict

import numpy as np


class StageTimer:
    """Per-stage timings in milliseconds. Keeps a rolling window (for live status)
    and totals for the whole run (for the final summary). Thread-safe."""

    def __init__(self, window: int = 300):
        self._window = window
        self._recent: Dict[str, deque] = {}
        self._sum: Dict[str, float] = {}
        self._count: Dict[str, int] = {}
        self._lock = threading.Lock()

    def record(self, stage: str, ms: float) -> None:
        with self._lock:
            self._recent.setdefault(stage, deque(maxlen=self._window)).append(ms)
            self._sum[stage] = self._sum.get(stage, 0.0) + ms
            self._count[stage] = self._count.get(stage, 0) + 1

    def summary(self) -> Dict[str, dict]:
        with self._lock:
            recent = {k: list(v) for k, v in self._recent.items()}
            totals = {k: (self._sum[k], self._count[k]) for k in self._sum}
        out = {}
        for stage, values in recent.items():
            arr = np.array(values)
            total, n = totals[stage]
            out[stage] = {
                "mean_ms": round(float(arr.mean()), 2),          # recent window
                "p95_ms": round(float(np.percentile(arr, 95)), 2),
                "max_ms": round(float(arr.max()), 2),
                "mean_all_ms": round(total / n, 2),              # whole run
                "n": n,
            }
        return out
