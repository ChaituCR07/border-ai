"""Overload shedding manager, adaptive analytics FPS, and rule-correctness floor (ADR 0042).

Enforces degradation order:
1. Live view shedding (lower MJPEG FPS / pause encoding when no viewers).
2. Per-camera adaptive analytics FPS (scales frame skipping while respecting analytics_fps_min floor).
3. ANPR budgeting (cap OCR calls, prioritize zone/watchlist vehicles).
4. Protected tier (alerts, event journal, and health heartbeats are NEVER shed).
5. State exposure: updates heartbeat and status with `degraded: true` and root-cause reasons.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DegradationPolicyConfig:
    freshness_headroom_ms: float = 250.0        # trigger adaptive skip when freshness > 250ms
    freshness_critical_ms: float = 450.0        # trigger live-view shedding when freshness > 450ms
    nominal_analytics_fps: float = 10.0         # target operational analytics FPS
    analytics_fps_min: float = 5.0              # hard floor; NEVER degrade below this to protect rules
    max_ocr_calls_per_sec: float = 10.0         # global OCR budget cap
    critical_camera_ids: List[str] = field(default_factory=lambda: ["CAM-01"])


@dataclass
class DegradationState:
    is_degraded: bool = False
    active_analytics_fps: float = 10.0
    live_view_shed: bool = False
    anpr_throttled: bool = False
    reasons: List[str] = field(default_factory=list)
    last_updated_s: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degraded": self.is_degraded,
            "active_analytics_fps": round(self.active_analytics_fps, 1),
            "live_view_shed": self.live_view_shed,
            "anpr_throttled": self.anpr_throttled,
            "reasons": list(self.reasons),
            "last_updated_s": round(self.last_updated_s, 2),
        }


class OverloadManager:
    """Monitors queue latencies and dynamically applies ADR 0042 graceful degradation."""

    def __init__(self, config: Optional[DegradationPolicyConfig] = None):
        self.config = config or DegradationPolicyConfig()
        self.state = DegradationState(active_analytics_fps=self.config.nominal_analytics_fps)

    def evaluate_health(self, current_freshness_p95_ms: float, queue_depth: int) -> DegradationState:
        """Assess pipeline freshness and adjust degradation state."""
        reasons = []
        now = time.time()
        active_fps = self.config.nominal_analytics_fps
        shed_live_view = False
        throttle_anpr = False

        # Phase 1: Live-view shedding if queueing is critical
        if current_freshness_p95_ms > self.config.freshness_critical_ms:
            shed_live_view = True
            reasons.append(
                f"Critical freshness ({current_freshness_p95_ms:.1f}ms > {self.config.freshness_critical_ms:.0f}ms): Live-view MJPEG encoding shed"
            )

        # Phase 2: Adaptive analytics frame skipping
        if current_freshness_p95_ms > self.config.freshness_headroom_ms:
            # Scale down FPS inversely with queue delay, but respect the floor
            reduction = min(1.0, (current_freshness_p95_ms - self.config.freshness_headroom_ms) / 300.0)
            target = self.config.nominal_analytics_fps - (reduction * (self.config.nominal_analytics_fps - self.config.analytics_fps_min))
            active_fps = max(self.config.analytics_fps_min, target)
            if active_fps < self.config.nominal_analytics_fps:
                reasons.append(
                    f"Adaptive frame skipping engaged ({active_fps:.1f} FPS, floor={self.config.analytics_fps_min:.1f} FPS)"
                )

        # Phase 3: High queue depth triggers ANPR budgeting
        if queue_depth > 15:
            throttle_anpr = True
            reasons.append(f"Queue depth ({queue_depth} frames): ANPR capped to restricted-zone vehicles only")

        is_degraded = bool(reasons)
        self.state = DegradationState(
            is_degraded=is_degraded,
            active_analytics_fps=active_fps,
            live_view_shed=shed_live_view,
            anpr_throttled=throttle_anpr,
            reasons=reasons,
            last_updated_s=now,
        )
        return self.state

    def should_process_frame(self, frame_index: int, camera_id: str) -> bool:
        """Determines whether a camera frame should be processed under the current degradation state."""
        # Critical cameras always maintain full nominal rate
        if camera_id in self.config.critical_camera_ids:
            return True

        # Calculate stride for active FPS relative to 25 FPS stream
        stride = max(1, int(round(25.0 / max(1.0, self.state.active_analytics_fps))))
        return (frame_index % stride) == 0

    def can_render_live_view(self, camera_id: str, active_viewers: int) -> bool:
        """Determines whether MJPEG encoding should proceed for this camera."""
        if active_viewers <= 0:
            return False
        if self.state.live_view_shed and camera_id not in self.config.critical_camera_ids:
            return False
        return True
