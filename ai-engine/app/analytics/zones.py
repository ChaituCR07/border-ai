from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple

import numpy as np

from app.analytics.geometry import point_in_polygon
from app.analytics.rules_config import ZoneRule
from app.schemas.events import (LOITERING, ZONE_DWELL, ZONE_ENTER, ZONE_EXIT,
                                Event, event_for)
from app.schemas.tracking import FrameTracks
from app.tracking.track_store import TrackStore, TrackUpdate


@dataclass
class _ZoneTrackState:
    spawned_inside: bool                     # first evaluated while already inside
    inside: bool = False                     # confirmed (hysteresis passed)
    in_streak: int = 0
    out_streak: int = 0
    first_inside_ts: float = 0.0             # first frame of the current inside streak
    enter_ts: float = 0.0
    last_inside_ts: float = 0.0
    dwell_alerted: bool = False
    loiter_alerted: bool = False
    window: Deque[Tuple[float, float, float]] = field(default_factory=deque)  # (ts, x, y)


class ZoneEngine:
    def __init__(self, zones: List[ZoneRule], min_track_hits: int = 3):
        self.zones = zones
        self.min_hits = min_track_hits
        self.occupancy: Dict[str, int] = {z.id: 0 for z in zones}
        self._state: Dict[Tuple[str, int], _ZoneTrackState] = {}   # (zone_id, track_id)
        self._poly_cache: Dict[Tuple[int, int], Dict[str, np.ndarray]] = {}

    # ---------- helpers ----------
    def _polygons(self, w: int, h: int) -> Dict[str, np.ndarray]:
        key = (w, h)
        if key not in self._poly_cache:
            self._poly_cache[key] = {
                z.id: np.array([[x * w, y * h] for x, y in z.polygon],
                               np.float32).reshape(-1, 1, 2)
                for z in self.zones}
        return self._poly_cache[key]

    # ---------- main entry ----------
    def update(self, ft: FrameTracks, store: TrackStore, upd: TrackUpdate) -> List[Event]:
        events: List[Event] = []
        if not self.zones:
            return events
        polys = self._polygons(ft.width, ft.height)

        for o in ft.tracks:
            track = store.get(o.track_id)
            if track is None or track.hits < self.min_hits:
                continue                                    # too young to trust
            for zone in self.zones:
                if zone.classes and o.label not in zone.classes:
                    continue
                point = o.bottom_center if zone.anchor == "bottom_center" else o.center
                inside_now = point_in_polygon(point, polys[zone.id])

                key = (zone.id, o.track_id)
                st = self._state.get(key)
                if st is None:
                    st = _ZoneTrackState(spawned_inside=inside_now)
                    self._state[key] = st
                events.extend(self._step(zone, st, o, point, inside_now, ft))

        events.extend(self._close_removed(upd, ft))
        self._refresh_occupancy()
        return events

    # ---------- per (zone, track) state machine ----------
    def _step(self, zone, st, o, point, inside_now, ft) -> List[Event]:
        out: List[Event] = []
        ts = ft.timestamp

        if not st.inside:
            if inside_now:
                if st.in_streak == 0:
                    st.first_inside_ts = ts
                st.in_streak += 1
                if st.in_streak >= zone.min_frames_inside:
                    st.inside = True
                    st.out_streak = 0
                    st.enter_ts = st.first_inside_ts
                    st.last_inside_ts = ts
                    st.dwell_alerted = False
                    st.loiter_alerted = False
                    st.window.clear()
                    out.append(event_for(
                        ZONE_ENTER, zone, "zone", ft, o.track_id, o.label,
                        o.confidence, o.bbox,
                        details={"spawned_inside": st.spawned_inside,
                                 "anchor": [round(point[0], 1), round(point[1], 1)]}))
                    st.spawned_inside = False          # later re-entries are real entries
            else:
                st.in_streak = 0
            return out

        # confirmed inside
        if inside_now:
            st.out_streak = 0
            st.last_inside_ts = ts
            dwell = ts - st.enter_ts

            if zone.loiter_s > 0:
                st.window.append((ts, point[0], point[1]))
                cutoff = ts - zone.loiter_s
                while st.window and st.window[0][0] < cutoff:
                    st.window.popleft()

            if zone.dwell_alert_s > 0 and not st.dwell_alerted and dwell >= zone.dwell_alert_s:
                st.dwell_alerted = True
                out.append(event_for(ZONE_DWELL, zone, "zone", ft, o.track_id, o.label,
                                     o.confidence, o.bbox, dwell_s=dwell))

            if zone.loiter_s > 0 and not st.loiter_alerted and dwell >= zone.loiter_s \
                    and len(st.window) > 1:
                xs = [p[1] for p in st.window]
                ys = [p[2] for p in st.window]
                span = max(max(xs) - min(xs), max(ys) - min(ys))
                if span <= zone.loiter_max_span * ft.width:
                    st.loiter_alerted = True
                    out.append(event_for(LOITERING, zone, "zone", ft, o.track_id, o.label,
                                         o.confidence, o.bbox, dwell_s=dwell,
                                         details={"span_px": round(span, 1)}))
        else:
            st.out_streak += 1
            if st.out_streak >= zone.min_frames_outside:
                st.inside = False
                st.in_streak = 0
                st.window.clear()
                out.append(event_for(ZONE_EXIT, zone, "zone", ft, o.track_id, o.label,
                                     o.confidence, o.bbox,
                                     dwell_s=st.last_inside_ts - st.enter_ts))
        return out

    # ---------- cleanup when the tracker finally removes a track ----------
    def _close_removed(self, upd: TrackUpdate, ft: FrameTracks) -> List[Event]:
        events: List[Event] = []
        for t in upd.removed:
            for zone in self.zones:
                st = self._state.pop((zone.id, t.track_id), None)
                if st is not None and st.inside:
                    events.append(event_for(
                        ZONE_EXIT, zone, "zone", ft, t.track_id, t.dominant_class,
                        t.last_confidence, t.last_bbox,
                        dwell_s=max(0.0, t.last_seen - st.enter_ts),
                        details={"reason": "track_ended"}))
        return events

    def _refresh_occupancy(self) -> None:
        counts = Counter(zid for (zid, _), st in self._state.items() if st.inside)
        self.occupancy = {z.id: counts.get(z.id, 0) for z in self.zones}
