import math
from typing import Tuple

import cv2
import numpy as np

Point = Tuple[float, float]


def signed_distance(p: Point, p1: Point, p2: Point) -> float:
    """Signed perpendicular distance from p to the infinite line p1 -> p2, in the
    units of the inputs. Positive on the side the normal (-dy, dx) points to
    (for a left-to-right horizontal line in image coordinates: below the line)."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0
    return (dx * (p[1] - p1[1]) - dy * (p[0] - p1[0])) / length


def crossing_within_segment(ref: Point, cur: Point, d_ref: float, d_cur: float,
                            p1: Point, p2: Point) -> bool:
    """ref and cur are on opposite sides of the infinite line (d_ref, d_cur have
    opposite signs). True if the movement ref -> cur passes through the line
    SEGMENT p1-p2, not just through its infinite extension."""
    t = d_ref / (d_ref - d_cur)
    x = ref[0] + t * (cur[0] - ref[0])
    y = ref[1] + t * (cur[1] - ref[1])
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    denom = dx * dx + dy * dy
    if denom == 0:
        return False
    u = ((x - p1[0]) * dx + (y - p1[1]) * dy) / denom
    return 0.0 <= u <= 1.0


def point_in_polygon(point: Point, polygon_px: np.ndarray) -> bool:
    """polygon_px: float32 array shaped (N, 1, 2). Points on the edge count as inside."""
    return cv2.pointPolygonTest(polygon_px, (float(point[0]), float(point[1])), False) >= 0
