import copy
from types import SimpleNamespace

from app.analytics.lines import LineEngine
from app.analytics.rules_config import parse_camera_rules
from app.analytics.zones import ZoneEngine
from app.behaviour.engine import BehaviourEngine
from app.schemas.events import Event
from app.schemas.tracking import FrameTracks, TrackedObject
from app.threat.config import parse_scoring_config
from app.threat.scorer import ThreatScorer
from app.tracking.track_store import TrackStore
from behaviour_helpers import ZONES_CFG, epoch, make_cfg, make_rule, obs
from rules_helpers import H, W

DEFAULT_SCORING = {
    "max_score": 100, "window_s": 600, "alert_min_score": 10, "cooldown_s": 60, "rearm_s": 300,
    "merge_by_plate": True, "merge_scope": "camera",
    "levels": [{"name": "LOW", "min": 0}, {"name": "MEDIUM", "min": 30},
               {"name": "HIGH", "min": 60}, {"name": "CRITICAL", "min": 80}],
    "bonus": {"multiple_suspicious": {"points": 10, "min_distinct_kinds": 4}},
    "sources": [
        {"id": "zone_violation", "label": "Restricted zone entry", "match": {"event_type": "ZONE_VIOLATION"}, "points": "from_event"},
        {"id": "direction_violation", "label": "Unauthorized direction", "match": {"event_type": "DIRECTION_VIOLATION"}, "points": "from_event"},
        {"id": "loitering", "label": "Loitering over 60 seconds", "match": {"event_type": "LOITERING_VIOLATION"}, "points": "from_event"},
        {"id": "after_hours", "label": "After-hours movement", "match": {"event_type": "AFTER_HOURS_ACTIVITY"}, "points": "from_event"},
        {"id": "unauthorized_vehicle_night", "label": "Unauthorized vehicle at night in a restricted zone",
         "match": {"event_type": "UNAUTHORIZED_VEHICLE_AFTER_HOURS"}, "points": "from_event"},
        {"id": "line_crossing", "label": "Virtual line crossing",
         "match": {"event_type": "LINE_CROSSING", "where": {"rule_type": "tripwire"}}, "points": 20,
         "excluded_by": ["direction_violation"]},
        {"id": "watchlist_vehicle", "label": "Watchlisted vehicle",
         "match": {"event_type": "WATCHLIST_MATCH", "where": {"details.entity_type": ["VEHICLE", "PLATE"]}},
         "points": 40, "status_multiplier": {"alert": 1.0, "review": 0.5}},
        {"id": "watchlist_person", "label": "Watchlisted person",
         "match": {"event_type": "WATCHLIST_MATCH", "where": {"details.entity_type": ["PERSON", "FACE"]}},
         "points": 50, "status_multiplier": {"alert": 1.0, "review": 0.5}},
    ],
}


def make_scoring(**over):
    data = copy.deepcopy(DEFAULT_SCORING)
    data.update(over)
    return parse_scoring_config({"scoring": data})


# ---------------------------------------------------------------- event builders
def beh(event_type, points, ts, track=1, cam="CAM", cls="person", rule_id="R001", severity="HIGH", **details):
    """A behaviour event as the Day 11 engine produces it."""
    return Event(type=event_type, camera_id=cam, timestamp=ts, frame_id=1, track_id=track, object_class=cls,
                 confidence=1.0, bbox=(0, 0, 10, 10), rule_id=rule_id, rule_name=rule_id, rule_kind="behaviour",
                 rule_type="rule", details={"severity": severity, "points": points, "reasons": ["test"], **details})


def zone_v(ts, **kw):
    return beh("ZONE_VIOLATION", 30, ts, rule_id="R001", **kw)


def direction_v(ts, **kw):
    return beh("DIRECTION_VIOLATION", 20, ts, rule_id="R002", severity="MEDIUM", **kw)


def after_hours(ts, **kw):
    return beh("AFTER_HOURS_ACTIVITY", 10, ts, rule_id="R004", severity="LOW", **kw)


def loitering(ts, **kw):
    return beh("LOITERING_VIOLATION", 15, ts, rule_id="R003", severity="MEDIUM", **kw)


def line_cross(ts, direction="IN", track=1, cam="CAM", cls="person", line="L1"):
    return obs("LINE_CROSSING", ts, track=track, cam=cam, cls=cls, rule_id=line, rule_type="tripwire",
               rule_kind="line", direction=direction)


def watch(ts, entity_type="VEHICLE", status="alert", risk="HIGH", track=1, cam="CAM", cls="car"):
    return obs("WATCHLIST_MATCH", ts, track=track, cam=cam, cls=cls, rule_id="WATCHLIST", rule_kind="watchlist",
               rule_type=entity_type.lower(),
               details={"status": status, "risk_level": risk, "entity_type": entity_type, "entry_id": 1})


def plate_ev(ts, plate, track=1, cam="CAM", cls="car"):
    return obs("PLATE_RECOGNIZED", ts, track=track, cam=cam, cls=cls, rule_id="ANPR", rule_kind="anpr",
               rule_type="plate", details={"plate": plate, "final": False})


def frame(cam, t, tracks, n=1):
    objs = [TrackedObject(tid, 0, cls, 0.9, 10, 10, 50, 100) for tid, cls in tracks]
    return FrameTracks(cam, n, t, 640, 480, objs)


class Bench:
    """Drives a ThreatScorer with synthetic events. Time moves by dt per step; advance() jumps ahead."""

    def __init__(self, scoring=None, dt=1.0, start=1_000_000.0, cam="CAM"):
        self.scorer = ThreatScorer(scoring or make_scoring())
        self.t, self.dt, self.cam, self.n, self.alerts = start, dt, cam, 0, []

    def advance(self, seconds):
        self.t += seconds

    def step(self, events=(), tracks=((1, "car"),), removed=()):
        self.n += 1
        events = list(events)
        if events:
            self.scorer.observe(self.cam, events)
        upd = SimpleNamespace(removed=[SimpleNamespace(track_id=t) for t in removed])
        out = self.scorer.update(frame(self.cam, self.t, tracks, self.n), upd)
        self.alerts += out
        self.t += self.dt
        return out

    def state(self, track=1):
        return self.scorer.current(self.cam, track)

    @property
    def levels(self):
        return [a.details["level"] for a in self.alerts]


# ---------------------------------------------------------------- real engines end to end
BEHAVIOUR_RULES = [
    make_rule("R001", [{"type": "object", "value": ["person", "car", "truck", "bus", "motorcycle", "bicycle"]},
                       {"type": "zone", "zone_type": "restricted"}], "ZONE_VIOLATION", "HIGH", 30),
    make_rule("R002", [{"type": "object", "value": ["person", "car", "truck", "bus", "motorcycle", "bicycle"]},
                       {"type": "line_crossing", "line": "L1", "expected_direction": "IN"}],
              "DIRECTION_VIOLATION", "MEDIUM", 20),
    make_rule("R003", [{"type": "object", "value": ["person"]}, {"type": "zone", "zone_type": "any", "min_dwell_s": 60}],
              "LOITERING_VIOLATION", "MEDIUM", 15),
    make_rule("R004", [{"type": "object", "value": ["person", "car", "truck", "bus", "motorcycle", "bicycle"]},
                       {"type": "time", "between": ["22:00", "05:00"]}, {"type": "track_age", "min_s": 2}],
              "AFTER_HOURS_ACTIVITY", "LOW", 10, rearm_s=3600),
]


class FullScene:
    """Zone + line engines, a real track store, the behaviour engine, and the threat scorer (640x480 frames).
    Zone Z1 covers x 352-608, y 120-360; line L1 is y = 240 (walking down crosses it going IN)."""

    def __init__(self, scoring=None, rules=None, start="2026-10-12 02:13:00", dt=1.0):
        rc = parse_camera_rules(ZONES_CFG)
        self.zones, self.lines = ZoneEngine(rc.zones, 3), LineEngine(rc.lines, 3)
        self.store = TrackStore("T", max_lost_frames=30)
        self.behaviour = BehaviourEngine(make_cfg(rules or BEHAVIOUR_RULES))
        self.scorer = ThreatScorer(scoring or make_scoring())
        self.t, self.dt, self.n = epoch(start), dt, 0
        self.alerts, self.behaviour_events = [], []

    def step(self, objs, extra_events=()):
        self.n += 1
        upd = self.store.update(objs, self.t)
        ft = FrameTracks("T", self.n, self.t, W, H, objs)
        observed = self.zones.update(ft, self.store, upd) + self.lines.update(ft, self.store, upd)
        self.behaviour.observe("T", observed + list(extra_events))
        beh_events = self.behaviour.update(ft, upd)
        self.scorer.observe("T", observed + beh_events + list(extra_events))
        alerts = self.scorer.update(ft, upd)
        self.behaviour_events += beh_events
        self.alerts += alerts
        self.t += self.dt
        return alerts

    def state(self, track=1):
        return self.scorer.current("T", track)

    @property
    def levels(self):
        return [a.details["level"] for a in self.alerts]
