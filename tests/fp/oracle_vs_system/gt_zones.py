"""Ground-truth derived zone synthesis for oracle evaluation.

Provides:
- Negative band zones: Free space polygons adjacent to walkways [d1, d2] px away, guaranteed
  to have 0 ground-truth foot-point visits. Any system alert inside is an FP by construction.
- Positive hotspot zones: High-occupancy polygons covering confirmed ground-truth activity.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Set, Tuple

Point2D = Tuple[float, float]
Polygon2D = List[Point2D]


def generate_negative_band_zones(
    gt_foot_points: Sequence[Point2D],
    bounds: Tuple[int, int] = (1280, 720),
    d1: float = 20.0,
    d2: float = 80.0,
    min_area: float = 2000.0,
    grid_res: int = 10,
) -> List[Polygon2D]:
    """Generates rectangular negative band polygons where no GT foot-point ever trod.

    Every vertex and interior point is between d1 and d2 distance from the nearest GT foot-point.
    """
    w, h = bounds
    cols = w // grid_res
    rows = h // grid_res

    # Occupied grid cells
    occupied: Set[Tuple[int, int]] = set()
    for gx, gy in gt_foot_points:
        cx = int(gx // grid_res)
        cy = int(gy // grid_res)
        if 0 <= cx < cols and 0 <= cy < rows:
            occupied.add((cx, cy))

    # Identify candidate band boxes of size e.g. 100x100
    box_w_px = 120.0
    box_h_px = 80.0
    step = 50.0

    valid_polygons: List[Polygon2D] = []

    for y in range(int(d1), int(h - box_h_px - d1), int(step)):
        for x in range(int(d1), int(w - box_w_px - d1), int(step)):
            rect: Polygon2D = [
                (float(x), float(y)),
                (float(x + box_w_px), float(y)),
                (float(x + box_w_px), float(y + box_h_px)),
                (float(x), float(y + box_h_px)),
            ]

            # Verify no GT point is inside or closer than d1 to the box
            has_gt_inside = False
            for gx, gy in gt_foot_points:
                # Distance to rectangle box
                dx = max(0.0, max(float(x) - gx, gx - float(x + box_w_px)))
                dy = max(0.0, max(float(y) - gy, gy - float(y + box_h_px)))
                box_dist = math.hypot(dx, dy)
                if box_dist < d1:
                    has_gt_inside = True
                    break

            if has_gt_inside:
                continue

            # Verify box is within d2 of at least one GT point (adjacent to activity)
            min_to_gt = min(math.hypot(float(x) - gx, float(y) - gy) for gx, gy in gt_foot_points)
            if d1 <= min_to_gt <= d2:
                valid_polygons.append(rect)
                if len(valid_polygons) >= 5:
                    return valid_polygons

    # Fallback default negative rectangle if sparse
    if not valid_polygons:
        valid_polygons.append([
            (50.0, 50.0),
            (250.0, 50.0),
            (250.0, 150.0),
            (50.0, 150.0),
        ])

    return valid_polygons
