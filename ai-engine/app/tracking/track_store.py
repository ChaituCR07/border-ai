from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from app.schemas.tracking import TrackedObject

ACTIVE, LOST, REMOVED = "ACTIVE", "LOST", "REMOVED"


@dataclass
class Track:
    track_id: int
    camera_id: str
    first_seen: float                       # seconds on the clock the caller supplies
    last_seen: float
    first_tick: int
    last_tick: int
    first_point: Tuple[float, float]        # ground-contact point where first seen
    trail: Deque[Tuple[float, float, float]]    # (timestamp, x, y), bounded
    state: str = ACTIVE
    hits: int = 0
    class_votes: Counter = field(default_factory=Counter)
    last_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    last_confidence: float = 0.0

    @property
    def dominant_class(self) -> str:
        return self.class_votes.most_common(1)[0][0] if self.class_votes else "unknown"

    @property
    def duration_s(self) -> float:
        return self.last_seen - self.first_seen

    @property
    def last_point(self) -> Tuple[float, float]:
        if self.trail:
            return (self.trail[-1][1], self.trail[-1][2])
        return self.first_point

    @property
    def displacement_px(self) -> float:
        (x0, y0), (x1, y1) = self.first_point, self.last_point
        return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5


@dataclass
class TrackUpdate:
    """What changed during one update. Week 2 uses these to finalize ANPR reads."""
    new: List[Track] = field(default_factory=list)
    lost: List[Track] = field(default_factory=list)
    reactivated: List[Track] = field(default_factory=list)
    removed: List[Track] = field(default_factory=list)


class TrackStore:
    """History for ONE camera. Call update() exactly once per tracker update."""

    def __init__(self, camera_id: str, max_lost_frames: int,
                 trail_length: int = 40, keep_finished: int = 2000):
        self.camera_id = camera_id
        self.max_lost_frames = max_lost_frames
        self.trail_length = trail_length
        self.tracks: Dict[int, Track] = {}                 # live: ACTIVE or LOST
        self.finished: Deque[Track] = deque(maxlen=keep_finished)
        self.tick = 0

    # ---------- main entry ----------
    def update(self, tracked: List[TrackedObject], timestamp: float) -> TrackUpdate:
        self.tick += 1
        upd = TrackUpdate()
        seen = set()

        for o in tracked:
            seen.add(o.track_id)
            t = self.tracks.get(o.track_id)
            if t is None:
                point = o.bottom_center
                t = Track(track_id=o.track_id, camera_id=self.camera_id,
                          first_seen=timestamp, last_seen=timestamp,
                          first_tick=self.tick, last_tick=self.tick,
                          first_point=point,
                          trail=deque(maxlen=self.trail_length))
                self.tracks[o.track_id] = t
                upd.new.append(t)
            elif t.state == LOST:
                t.state = ACTIVE
                upd.reactivated.append(t)

            t.last_seen = timestamp
            t.last_tick = self.tick
            t.hits += 1
            t.class_votes[o.class_name] += o.confidence       # confidence-weighted vote
            t.trail.append((timestamp, *o.bottom_center))
            t.last_bbox = o.bbox
            t.last_confidence = o.confidence

            o.stable_class = t.dominant_class
            o.age_s = t.duration_s

        for tid, t in list(self.tracks.items()):
            if tid in seen:
                continue
            if t.state == ACTIVE:
                t.state = LOST
                upd.lost.append(t)
            if self.tick - t.last_tick > self.max_lost_frames:
                t.state = REMOVED
                del self.tracks[tid]
                self.finished.append(t)
                upd.removed.append(t)

        return upd

    # ---------- queries ----------
    def get(self, track_id: int) -> Optional[Track]:
        return self.tracks.get(track_id)

    def active_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if t.state == ACTIVE]

    def lost_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if t.state == LOST]

    def all_tracks(self) -> List[Track]:
        """Finished + live tracks (use at the end of a clip for statistics)."""
        return list(self.finished) + list(self.tracks.values())
