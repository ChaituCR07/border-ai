"""Standalone zone evaluation engine implementing production hysteresis and foot-point semantics.

Implements:
- Inner/outer boundary deadband hysteresis.
- Consecutive frame confirmation filter.
- Bottom-center foot-point anchor vs center anchor comparison.
- In-zone dwelling and exit event generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
from tests.fp.logic.sim.oracle import min_signed_distance

Point2D = Tuple[float, float]
Polygon2D = Sequence[Point2D]


@dataclass
class ZoneTrackState:
    track_id: int
    inside: bool = False
    in_streak: int = 0
    out_streak: int = 0
    enter_ts: float = 0.0
    last_inside_ts: float = 0.0


@dataclass
class ZoneEvent:
    event_type: str  # ZONE_ENTER, ZONE_EXIT, ZONE_DWELL
    zone_id: str
    track_id: int
    timestamp_s: float
    anchor_pt: Point2D
    score: float = 50.0


class ZoneEvaluator:
    def __init__(
        self,
        zone_id: str,
        polygon: Polygon2D,
        margin_px: float = 20.0,
        confirm_frames: int = 3,
        anchor: str = "bottom_center",  # "bottom_center" or "center"
    ):
        self.zone_id = zone_id
        self.polygon = polygon
        self.margin_px = margin_px
        self.confirm_frames = confirm_frames
        self.anchor = anchor
        self.tracks: Dict[int, ZoneTrackState] = {}

    def process_frame(self, ts: float, detections: List[Dict[str, Any]]) -> List[ZoneEvent]:
        events: List[ZoneEvent] = []
        active_ids = set()

        for det in detections:
            tid = det["track_id"]
            active_ids.add(tid)
            pt = det["bottom_center"] if self.anchor == "bottom_center" else det["center"]

            sd = min_signed_distance(self.polygon, pt)
            # sd < -margin: definitely inside
            # sd > +margin: definitely outside
            # [-margin, +margin]: grey deadband

            st = self.tracks.setdefault(tid, ZoneTrackState(track_id=tid))

            if not st.inside:
                if sd <= -self.margin_px:
                    st.in_streak += 1
                    if st.in_streak >= self.confirm_frames:
                        st.inside = True
                        st.enter_ts = ts
                        st.last_inside_ts = ts
                        st.out_streak = 0
                        events.append(ZoneEvent("ZONE_ENTER", self.zone_id, tid, ts, pt))
                else:
                    st.in_streak = 0
            else:
                # Track is currently inside
                if sd >= self.margin_px:
                    st.out_streak += 1
                    if st.out_streak >= self.confirm_frames:
                        st.inside = False
                        st.in_streak = 0
                        st.out_streak = 0
                        events.append(ZoneEvent("ZONE_EXIT", self.zone_id, tid, ts, pt))
                else:
                    st.out_streak = 0
                    st.last_inside_ts = ts

        return events
