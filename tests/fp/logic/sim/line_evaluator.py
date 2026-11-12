"""Standalone line crossing evaluator implementing debounce, directional logic, and class filtering.

Enforces:
- Directed segment orientation check (positive vs negative side).
- Deadband deadzone to prevent jitter crossings.
- Permitted vs wrong-way crossing direction violation classification.
- Cooldown and spatial-temporal ID switch deduplication.
- Class filtering (e.g. vehicle-only counting lines).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

Point2D = Tuple[float, float]


@dataclass
class LineTrackState:
    track_id: int
    cls: str
    side: int = 0  # -1, +1, or 0 (undecided)
    ref_pt: Point2D = (0.0, 0.0)
    ref_dist: float = 0.0
    last_event_ts: float = float("-inf")


@dataclass
class LineEvent:
    event_type: str  # LINE_CROSSING, LINE_CROSSING_WRONG_DIRECTION
    line_id: str
    track_id: int
    cls: str
    direction: int  # +1 or -1
    timestamp_s: float
    point: Point2D


class LineEvaluator:
    def __init__(
        self,
        line_id: str,
        p1: Point2D,
        p2: Point2D,
        permitted_direction: int = 1,  # +1 is normal flow, -1 is reverse flow
        deadband_px: float = 15.0,
        cooldown_s: float = 2.0,
        allowed_classes: Optional[Set[str]] = None,
        dedupe_radius_px: float = 50.0,
        dedupe_dt_s: float = 1.0,
    ):
        self.line_id = line_id
        self.p1 = p1
        self.p2 = p2
        self.permitted_dir = permitted_direction
        self.deadband_px = deadband_px
        self.cooldown_s = cooldown_s
        self.allowed_classes = allowed_classes
        self.dedupe_radius_px = dedupe_radius_px
        self.dedupe_dt_s = dedupe_dt_s

        self.tracks: Dict[int, LineTrackState] = {}
        self.recent_crossings: List[Tuple[float, Point2D, int]] = []  # (ts, pt, dir)

    def _signed_dist(self, p: Point2D) -> float:
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        length = math.hypot(dx, dy)
        if length == 0.0:
            return 0.0
        return (dx * (p[1] - self.p1[1]) - dy * (p[0] - self.p1[0])) / length

    def _intersects_segment(self, ref: Point2D, cur: Point2D, d_ref: float, d_cur: float) -> bool:
        if (d_ref > 0 and d_cur > 0) or (d_ref < 0 and d_cur < 0) or (d_ref == d_cur):
            return False
        t = d_ref / (d_ref - d_cur)
        ix = ref[0] + t * (cur[0] - ref[0])
        iy = ref[1] + t * (cur[1] - ref[1])
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        denom = dx * dx + dy * dy
        if denom == 0.0:
            return False
        u = ((ix - self.p1[0]) * dx + (iy - self.p1[1]) * dy) / denom
        return 0.0 <= u <= 1.0

    def process_frame(self, ts: float, detections: List[Dict[str, Any]]) -> List[LineEvent]:
        events: List[LineEvent] = []

        # Prune old dedupe crossings
        self.recent_crossings = [
            (cts, cpt, cdir) for cts, cpt, cdir in self.recent_crossings if ts - cts <= self.dedupe_dt_s
        ]

        for det in detections:
            tid = det["track_id"]
            cls = det["cls"]
            if self.allowed_classes and cls not in self.allowed_classes:
                continue

            pt = det["bottom_center"]
            d = self._signed_dist(pt)

            st = self.tracks.setdefault(tid, LineTrackState(track_id=tid, cls=cls))

            if abs(d) <= self.deadband_px:
                # Inside deadband deadzone: don't commit
                continue

            current_side = 1 if d > 0 else -1

            if st.side == 0:
                # First observation outside deadband: establish baseline side
                st.side = current_side
                st.ref_pt = pt
                st.ref_dist = d
            elif st.side != current_side:
                # Potential crossing!
                if self._intersects_segment(st.ref_pt, pt, st.ref_dist, d):
                    direction = current_side  # +1 if crossing from -1 to +1, -1 if crossing from +1 to -1

                    # Check spatial-temporal deduplication (e.g. ID switch near crossing)
                    is_duplicate = False
                    for cts, cpt, cdir in self.recent_crossings:
                        if cdir == direction and math.hypot(pt[0] - cpt[0], pt[1] - cpt[1]) <= self.dedupe_radius_px:
                            is_duplicate = True
                            break

                    # Check track cooldown
                    if not is_duplicate and (ts - st.last_event_ts >= self.cooldown_s):
                        ev_type = (
                            "LINE_CROSSING"
                            if direction == self.permitted_dir
                            else "LINE_CROSSING_WRONG_DIRECTION"
                        )
                        events.append(LineEvent(ev_type, self.line_id, tid, cls, direction, ts, pt))
                        st.last_event_ts = ts
                        self.recent_crossings.append((ts, pt, direction))

                # Transition to new side
                st.side = current_side
                st.ref_pt = pt
                st.ref_dist = d
            else:
                # Same side, update reference point
                st.ref_pt = pt
                st.ref_dist = d

        return events
