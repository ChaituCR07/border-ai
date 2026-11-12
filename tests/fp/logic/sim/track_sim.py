"""Synthetic track generator for property and boundary testing.

Simulates:
- Continuous piecewise-linear movement across waypoints.
- Configurable foot-point Gaussian jitter.
- Random per-frame detection dropouts.
- Perspective-scaled bounding box height and width.
- Production-compatible FrameTracks / tracker output schema.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


@dataclass
class SimTrack:
    track_id: int
    cls: str
    foot: List[Tuple[float, float]]
    box_h: List[float]
    conf: List[float]
    present: List[bool]

    @property
    def num_frames(self) -> int:
        return len(self.foot)


def default_h_at(y: float) -> float:
    """Default perspective height scaling: taller near camera (bottom of image)."""
    return max(20.0, 40.0 + 0.25 * y)


def walk(
    waypoints: List[Tuple[float, float]],
    speed_px_s: float,
    fps: float,
    seed: int = 42,
    jitter_sigma: float = 0.0,
    dropout_p: float = 0.0,
    conf_mean: float = 0.85,
    id_: int = 1,
    cls: str = "person",
    h_at: Optional[Callable[[float], float]] = None,
) -> SimTrack:
    """Generates a piecewise-linear path sampled at fps with optional jitter and dropouts."""
    if len(waypoints) < 2:
        raise ValueError("At least 2 waypoints are required to construct a path")
    if speed_px_s <= 0:
        raise ValueError("speed_px_s must be > 0")
    if fps <= 0:
        raise ValueError("fps must be > 0")

    h_fn = h_at or default_h_at
    rng = random.Random(seed)

    raw_pts: List[Tuple[float, float]] = []
    for a, b in zip(waypoints[:-1], waypoints[1:]):
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        num_steps = max(1, int(round((dist / speed_px_s) * fps)))
        for i in range(num_steps):
            t = i / float(num_steps)
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            raw_pts.append((x, y))

    # Add final endpoint
    raw_pts.append(waypoints[-1])

    foot_pts: List[Tuple[float, float]] = []
    box_h_list: List[float] = []
    conf_list: List[float] = []
    present_list: List[bool] = []

    for x, y in raw_pts:
        if jitter_sigma > 0.0:
            jx = rng.gauss(0.0, jitter_sigma)
            jy = rng.gauss(0.0, jitter_sigma)
            fx = x + jx
            fy = y + jy
        else:
            fx, fy = x, y

        is_present = (rng.random() >= dropout_p) if dropout_p > 0.0 else True
        c = max(0.05, min(0.99, rng.gauss(conf_mean, 0.05)))
        bh = h_fn(fy)

        foot_pts.append((fx, fy))
        box_h_list.append(bh)
        conf_list.append(c)
        present_list.append(is_present)

    return SimTrack(
        track_id=id_,
        cls=cls,
        foot=foot_pts,
        box_h=box_h_list,
        conf=conf_list,
        present=present_list,
    )


def to_frames(tracks: List[SimTrack], fps: float) -> Iterator[Tuple[float, List[Dict[str, Any]]]]:
    """Yields (timestamp_s, detections_list) for each frame index across all sim tracks."""
    if not tracks:
        return

    max_len = max(t.num_frames for t in tracks)
    for frame_idx in range(max_len):
        ts = frame_idx / fps
        frame_items: List[Dict[str, Any]] = []

        for tr in tracks:
            if frame_idx < tr.num_frames and tr.present[frame_idx]:
                fx, fy = tr.foot[frame_idx]
                bh = tr.box_h[frame_idx]
                bw = bh * (0.4 if tr.cls == "person" else 1.2)  # human vs vehicle aspect ratio
                x1 = fx - bw / 2.0
                y1 = fy - bh
                x2 = fx + bw / 2.0
                y2 = fy
                frame_items.append({
                    "track_id": tr.track_id,
                    "cls": tr.cls,
                    "foot": (fx, fy),
                    "center": (fx, fy - bh / 2.0),
                    "bottom_center": (fx, fy),
                    "h": bh,
                    "w": bw,
                    "bbox_xyxy": (x1, y1, x2, y2),
                    "conf": tr.conf[frame_idx],
                })

        yield ts, frame_items
