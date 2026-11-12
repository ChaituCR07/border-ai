"""Analytical 2D geometric ground-truth oracle for zone and line evaluations.

Provides:
- Exact signed distance from a point to arbitrary 2D polygons (negative inside, positive outside).
- Zone persistence qualification (continuous frames deeper than margin).
- Signed segment crossing direction (+1, -1, or 0) using exact 2D orientation tests.
- Support for Shapely if available, with identical pure-Python fallbacks.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

Point2D = Tuple[float, float]
Polygon2D = Sequence[Point2D]

try:
    from shapely.geometry import LineString as _S_LineString  # type: ignore
    from shapely.geometry import Point as _S_Point
    from shapely.geometry import Polygon as _S_Polygon
    _HAS_SHAPELY = True
except ImportError:
    _HAS_SHAPELY = False


def point_in_polygon_2d(poly: Polygon2D, pt: Point2D) -> bool:
    """Ray casting point-in-polygon test."""
    x, y = pt
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y):
            if x <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def dist_point_to_segment(p: Point2D, a: Point2D, b: Point2D) -> float:
    """Minimum Euclidean distance from point p to segment [a, b]."""
    px, py = p
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0.0:
        return math.hypot(px - ax, py - ay)

    # Project p onto ab: t in [0, 1]
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def min_boundary_distance(poly: Polygon2D, pt: Point2D) -> float:
    """Minimum distance from point to the boundary edges of poly."""
    n = len(poly)
    if n < 3:
        raise ValueError("Polygon must have at least 3 vertices")
    min_d = float("inf")
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        d = dist_point_to_segment(pt, a, b)
        if d < min_d:
            min_d = d
    return min_d


def min_signed_distance(poly: Polygon2D, pt: Point2D) -> float:
    """Signed distance to polygon: negative inside, positive outside, 0 on edge."""
    if _HAS_SHAPELY:
        spoly = _S_Polygon(poly)
        spt = _S_Point(pt)
        d = spoly.exterior.distance(spt)
        return -d if spoly.contains(spt) else d

    # Pure Python implementation
    inside = point_in_polygon_2d(poly, pt)
    boundary_d = min_boundary_distance(poly, pt)
    return -boundary_d if inside else boundary_d


def oracle_zone_entry(
    poly: Polygon2D,
    foot_path: Sequence[Point2D],
    margin_px: float,
    min_frames: int,
) -> bool:
    """True if foot_path is deeper than margin_px inside poly for >= min_frames consecutive frames."""
    run = 0
    for p in foot_path:
        sd = min_signed_distance(poly, p)
        if sd < -margin_px:
            run += 1
            if run >= min_frames:
                return True
        else:
            run = 0
    return False


def oracle_never_near(
    poly: Polygon2D,
    foot_path: Sequence[Point2D],
    margin_px: float,
) -> bool:
    """True if all points in foot_path stay strictly > margin_px outside the polygon."""
    return all(min_signed_distance(poly, p) > margin_px for p in foot_path)


def signed_distance_to_line(p: Point2D, p1: Point2D, p2: Point2D) -> float:
    """Perpendicular signed distance from p to infinite directed line p1 -> p2."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0.0:
        return 0.0
    # Positive on right side of directed line: (dx*(py - y1) - dy*(px - x1))
    return (dx * (p[1] - p1[1]) - dy * (p[0] - p1[0])) / length


def oracle_crossing_direction(
    p1: Point2D,
    p2: Point2D,
    foot_path: Sequence[Point2D],
    deadband_px: float = 0.0,
) -> int:
    """Evaluates crossing direction of a foot path across line segment [p1, p2].

    Returns:
        +1 for crossing from negative side to positive side,
        -1 for crossing from positive side to negative side,
        0 for no valid crossing.
    """
    if len(foot_path) < 2:
        return 0

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return 0

    # Track last committed side beyond deadband
    committed_side = 0

    for prev_pt, cur_pt in zip(foot_path[:-1], foot_path[1:]):
        d_prev = signed_distance_to_line(prev_pt, p1, p2)
        d_cur = signed_distance_to_line(cur_pt, p1, p2)

        if abs(d_prev) > deadband_px and committed_side == 0:
            committed_side = 1 if d_prev > 0 else -1

        # Check for side transition
        if committed_side != 0:
            cur_side = 1 if d_cur > deadband_px else (-1 if d_cur < -deadband_px else 0)
            if cur_side != 0 and cur_side != committed_side:
                # Check if segment [prev_pt, cur_pt] intersects line segment [p1, p2]
                if (d_prev > 0 and d_cur < 0) or (d_prev < 0 and d_cur > 0):
                    t = d_prev / (d_prev - d_cur)
                    ix = prev_pt[0] + t * (cur_pt[0] - prev_pt[0])
                    iy = prev_pt[1] + t * (cur_pt[1] - prev_pt[1])
                    u = ((ix - p1[0]) * dx + (iy - p1[1]) * dy) / denom
                    if 0.0 <= u <= 1.0:
                        return 1 if committed_side == -1 else -1

    return 0
