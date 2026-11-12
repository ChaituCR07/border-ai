"""Video and coordinate stress augmentations for robustness analysis.

Applies parameterised perturbations:
- Camera shake / translation jitter: frame-by-frame (dx, dy) coordinate offset.
- Camera calibration drift: steady monotonic pixel translation per minute.
- Illumination drop and night noise: confidence attenuation and coordinate variance.
- Detection dropouts: dropout probability stress test.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class StressConfig:
    shake_sigma_px: float = 0.0
    drift_rate_px_s: float = 0.0  # e.g. 5px per minute = 5/60 px/s
    confidence_drop: float = 0.0
    dropout_prob: float = 0.0


def apply_camera_shake(
    detections: List[Dict[str, Any]],
    shift_xy: Tuple[float, float],
) -> List[Dict[str, Any]]:
    """Applies a global coordinate translation (camera bump or shake) to all frame detections."""
    dx, dy = shift_xy
    augmented = []
    for det in detections:
        d = dict(det)
        if "bottom_center" in d:
            bx, by = d["bottom_center"]
            d["bottom_center"] = (bx + dx, by + dy)
        if "center" in d:
            cx, cy = d["center"]
            d["center"] = (cx + dx, cy + dy)
        if "foot" in d:
            fx, fy = d["foot"]
            d["foot"] = (fx + dx, fy + dy)
        if "bbox_xyxy" in d:
            x1, y1, x2, y2 = d["bbox_xyxy"]
            d["bbox_xyxy"] = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        augmented.append(d)
    return augmented


def generate_stress_stream(
    frame_stream: List[Tuple[float, List[Dict[str, Any]]]],
    config: StressConfig,
    seed: int = 42,
) -> List[Tuple[float, List[Dict[str, Any]]]]:
    """Generates perturbed detection stream according to stress configuration."""
    rng = random.Random(seed)
    augmented_stream = []

    for ts, dets in frame_stream:
        # Calculate instantaneous shift (drift + shake)
        drift_x = config.drift_rate_px_s * ts
        shake_x = rng.gauss(0.0, config.shake_sigma_px) if config.shake_sigma_px > 0.0 else 0.0
        shake_y = rng.gauss(0.0, config.shake_sigma_px) if config.shake_sigma_px > 0.0 else 0.0

        total_shift = (drift_x + shake_x, shake_y)

        shifted_dets = apply_camera_shake(dets, total_shift)

        # Apply dropouts and confidence drops
        final_dets = []
        for d in shifted_dets:
            if config.dropout_prob > 0.0 and rng.random() < config.dropout_prob:
                continue  # Dropped frame

            if config.confidence_drop > 0.0:
                d["conf"] = max(0.05, d.get("conf", 0.8) - config.confidence_drop)

            final_dets.append(d)

        augmented_stream.append((ts, final_dets))

    return augmented_stream
