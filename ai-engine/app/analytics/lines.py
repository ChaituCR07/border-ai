from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.analytics.geometry import crossing_within_segment, signed_distance
from app.analytics.rules_config import LineRule, opposite
from app.schemas.events import LINE_CROSSING, Event, event_for
from app.schemas.tracking import FrameTracks
from app.tracking.track_store import TrackStore, TrackUpdate


@dataclass
class _LineTrackState:
    side: int = 0                                  # committed side: -1, +1, or 0 (undecided)
    ref: Tuple[float, float] = (0.0, 0.0)          # last point beyond the band on that side
    ref_dist: float = 0.0
    last_event_ts: float = float("-inf")


class LineEngine:
    def __init__(self, lines: List[LineRule], min_track_hits: int = 3):
        self.lines = lines
        self.min_hits = min_track_hits
        self.counts: Dict[str, Dict[str, int]] = {ln.id: {"IN": 0, "OUT": 0} for ln in lines}
        self._state: Dict[Tuple[str, int], _LineTrackState] = {}   # (line_id, track_id)

    def update(self, ft: FrameTracks, store: TrackStore, upd: TrackUpdate) -> List[Event]:
        events: List[Event] = []
        if not self.lines:
            return events
        w, h = ft.width, ft.height

        for o in ft.tracks:
            track = store.get(o.track_id)
            if track is None or track.hits < self.min_hits:
                continue
            for ln in self.lines:
                if ln.classes and o.label not in ln.classes:
                    continue
                p1 = (ln.p1[0] * w, ln.p1[1] * h)
                p2 = (ln.p2[0] * w, ln.p2[1] * h)
                point = o.bottom_center if ln.anchor == "bottom_center" else o.center

                d = signed_distance(point, p1, p2)
                band = ln.hysteresis * w
                if abs(d) <= band:
                    continue                                  # inside the dead band: undecided

                side = 1 if d > 0 else -1
                key = (ln.id, o.track_id)
                st = self._state.get(key)
                if st is None:
                    st = _LineTrackState()
                    self._state[key] = st

                if st.side == 0 or side == st.side:           # first sighting or same side
                    st.side, st.ref, st.ref_dist = side, point, d
                    continue

                # The track is now clearly on the other side
                crossed = crossing_within_segment(st.ref, point, st.ref_dist, d, p1, p2)
                direction = ln.positive_direction if side > 0 else opposite(ln.positive_direction)
                suppressed = (ft.timestamp - st.last_event_ts) < ln.cooldown_s

                if crossed and not suppressed:
                    st.last_event_ts = ft.timestamp
                    self.counts[ln.id][direction] += 1
                    events.append(event_for(
                        LINE_CROSSING, ln, "line", ft, o.track_id, o.label,
                        o.confidence, o.bbox, direction=direction,
                        details={"anchor": [round(point[0], 1), round(point[1], 1)],
                                 "band_px": round(band, 1)}))

                # Commit the new side either way (walked around the end, or suppressed)
                st.side, st.ref, st.ref_dist = side, point, d

        for t in upd.removed:
            for ln in self.lines:
                self._state.pop((ln.id, t.track_id), None)
        return events
