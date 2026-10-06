from app.schemas.tracking import FrameTracks, TrackedObject
from app.tracking.track_store import TrackStore

W, H = 640, 480


def obj(tid, x, y, name="person", conf=0.9):
    """A tracked object whose ground-contact point (bottom-center) is exactly (x, y)."""
    return TrackedObject(tid, 0, name, conf, x - 20, y - 80, x + 20, y)


class Harness:
    """Feeds synthetic frames through a TrackStore and a rule engine
    (a ZoneEngine or LineEngine), collecting every event."""

    def __init__(self, engine, dt=0.1):
        self.engine = engine
        self.store = TrackStore("T", max_lost_frames=30)
        self.t, self.dt, self.frame = 0.0, dt, 0
        self.events = []

    def step(self, objs):
        self.frame += 1
        upd = self.store.update(objs, self.t)
        ft = FrameTracks("T", self.frame, self.t, W, H, objs)
        new = self.engine.update(ft, self.store, upd)
        self.events.extend(new)
        self.t += self.dt
        return new

    @property
    def types(self):
        return [e.type for e in self.events]
