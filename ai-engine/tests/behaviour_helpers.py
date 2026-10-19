from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.analytics.lines import LineEngine
from app.analytics.rules_config import parse_camera_rules
from app.analytics.zones import ZoneEngine
from app.behaviour.engine import BehaviourEngine
from app.behaviour.rules_config import parse_behaviour_config
from app.schemas.events import Event
from app.schemas.tracking import FrameTracks, TrackedObject
from app.tracking.track_store import TrackStore
from rules_helpers import H, W, obj

IST = ZoneInfo("Asia/Kolkata")


def epoch(local: str, tz=IST) -> float:
    """'2026-10-12 02:13:00' read in the given zone -> epoch seconds."""
    return datetime.fromisoformat(local).replace(tzinfo=tz).timestamp()


def make_rule(rule_id="R1", conditions=None, event_type="TEST_RULE", severity="HIGH", score=30, **kw):
    r = {"rule_id": rule_id, "name": f"Rule {rule_id}", "event_type": event_type,
         "conditions": conditions or [{"type": "object", "value": "person"}],
         "action": {"severity": severity, "score": score}}
    r.update(kw)
    return r


def make_cfg(rules, tz="Asia/Kolkata", **top):
    data = {"version": 1, "site": {"timezone": tz}, "rules": rules}
    data.update(top)
    return parse_behaviour_config(data)


def obs(type_, ts, track=1, cam="CAM", cls="person", rule_id="Z1", rule_type="restricted",
        rule_kind="zone", direction=None, details=None):
    return Event(type=type_, camera_id=cam, timestamp=ts, frame_id=1, track_id=track, object_class=cls,
                 confidence=0.9, bbox=(0, 0, 10, 10), rule_id=rule_id, rule_name=rule_id,
                 rule_kind=rule_kind, rule_type=rule_type, direction=direction, details=details or {})


class Scene:
    """Drives a BehaviourEngine with synthetic frames. Tracks are (id, class) pairs; time moves by dt."""

    def __init__(self, rules, start="2026-10-12 12:00:00", dt=1.0, cam="CAM", authorized=None, **cfg_kw):
        self.engine = BehaviourEngine(make_cfg(rules, **cfg_kw), authorized)
        self.t, self.dt, self.cam, self.n, self.first = epoch(start), dt, cam, 0, {}

    def step(self, tracks=((1, "person"),), events=(), removed=()):
        self.n += 1
        objs = []
        for tid, cls in tracks:
            self.first.setdefault(tid, self.t)
            o = TrackedObject(tid, 0, cls, 0.9, 10, 10, 50, 100)
            o.age_s = self.t - self.first[tid]
            objs.append(o)
        if events:
            self.engine.observe(self.cam, list(events))
        ft = FrameTracks(self.cam, self.n, self.t, 640, 480, objs)
        out = self.engine.update(ft, SimpleNamespace(removed=[SimpleNamespace(track_id=t) for t in removed]))
        self.t += self.dt
        return out

    def run(self, n, **kw):
        out = []
        for _ in range(n):
            out += self.step(**kw)
        return out


# ---------------------------------------------------------------- real geometry (Day 6 engines)
ZONES_CFG = {
    "camera_id": "T",
    # restricted zone on the right half; line L1 across the full width (positive side = down = IN)
    "zones": [{"id": "Z1", "name": "Restricted", "type": "restricted",
               "polygon": [[0.55, 0.25], [0.95, 0.25], [0.95, 0.75], [0.55, 0.75]]}],
    "lines": [{"id": "L1", "name": "Entry", "p1": [0, 0.5], "p2": [1, 0.5],
               "positive_direction": "IN", "cooldown_s": 0}],
}


class GeometryScene:
    """Real ZoneEngine + LineEngine + TrackStore feeding a BehaviourEngine (640x480 frames).
    Zone Z1 covers x 352-608, y 120-360. Line L1 is y = 240; walking down crosses it going IN."""

    def __init__(self, rules, start="2026-10-12 12:00:00", dt=1.0, authorized=None, **cfg_kw):
        if any(c.get("type") == "plate" and "authorized" in c
               for r in rules
               for c in (r.get("conditions") if isinstance(r, dict) else getattr(r, "conditions", []))):
            cfg_kw.setdefault("authorized_plates_csv", "configs/authorized_plates_demo.csv")
        rc = parse_camera_rules(ZONES_CFG)
        self.zones, self.lines = ZoneEngine(rc.zones, 3), LineEngine(rc.lines, 3)
        self.store = TrackStore("T", max_lost_frames=30)
        self.behaviour = BehaviourEngine(make_cfg(rules, **cfg_kw), authorized)
        self.t, self.dt, self.n = epoch(start), dt, 0
        self.observations, self.results = [], []

    def step(self, objs, extra_events=()):
        self.n += 1
        upd = self.store.update(objs, self.t)
        ft = FrameTracks("T", self.n, self.t, W, H, objs)
        obs_events = self.zones.update(ft, self.store, upd) + self.lines.update(ft, self.store, upd)
        self.observations += obs_events
        self.behaviour.observe("T", obs_events + list(extra_events))
        out = self.behaviour.update(ft, upd)
        self.results += out
        self.t += self.dt
        return out

    @property
    def types(self):
        return [e.type for e in self.results]
