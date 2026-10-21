import logging
import threading
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.schemas.events import PLATE_RECOGNIZED, THREAT_ALERT, Event
from app.threat.config import LEVEL_RANK, ScoringConfig, Source, source_matches
from app.threat.scoring import ScoreResult, total_score
from app.utils.timeutil import to_iso_utc

log = logging.getLogger("threat")

PRUNE_EVERY_S = 60.0


@dataclass
class Contribution:
    kind: str
    label: str
    points: int
    at: float                                   # when this kind of evidence was last seen
    event_type: str
    event_id: str
    discriminator: str
    reasons: List[str]
    camera_id: str
    track_id: int

    def to_dict(self) -> dict:
        return {"kind": self.kind, "label": self.label, "points": self.points,
                "event_type": self.event_type, "event_id": self.event_id,
                "at": to_iso_utc(self.at), "reasons": self.reasons}


@dataclass
class EntityState:
    key: tuple
    camera_id: str
    track_id: int
    object_class: str = "unknown"
    plate: Optional[str] = None
    contributions: Dict[str, Dict[str, Contribution]] = field(default_factory=dict)   # kind -> discriminator -> c
    last_activity: float = 0.0
    last_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    last_frame_id: int = 0
    score: int = 0
    level: str = "LOW"
    result: Optional[ScoreResult] = None
    kept: List[Contribution] = field(default_factory=list)
    alerted_level: Optional[str] = None
    last_alert_ts: Optional[float] = None
    below_since: Optional[float] = None


@dataclass
class ThreatState:
    entity: str
    camera_id: str
    track_id: int
    plate: Optional[str]
    object_class: str
    score: int
    level: str
    raw: int
    bonus: int
    capped: bool
    counted: Dict[str, int]
    excluded: List[str]
    contributions: List[Contribution]


def _entity_name(key: tuple) -> str:
    return f"plate:{key[2]}" if key[0] == "plate" else f"{key[1]}#{key[2]}"


class ThreatScorer:
    def __init__(self, cfg: ScoringConfig):
        self.cfg = cfg
        self.stats: Counter = Counter()
        self.alerts_by_level: Counter = Counter()
        self._lock = threading.Lock()
        self._inbox: Dict[str, List[Event]] = {}
        self._entities: Dict[tuple, EntityState] = {}
        self._track_map: Dict[Tuple[str, int], tuple] = {}
        self._last_prune = 0.0

    # ------------------------------------------------------------------ input
    def observe(self, camera_id: str, events: List[Event]) -> None:
        """Thread-safe. THREAT_ALERT events (our own output) are ignored."""
        events = [e for e in events if e.rule_kind != "threat"]
        if events:
            with self._lock:
                self._inbox.setdefault(camera_id, []).extend(events)

    # ------------------------------------------------------------------ events -> contributions
    def _entity_for(self, camera_id: str, track_id: int) -> EntityState:
        key = self._track_map.get((camera_id, track_id))
        st = self._entities.get(key) if key is not None else None
        if st is None:
            key = ("track", camera_id, track_id)
            st = self._entities.setdefault(key, EntityState(key, camera_id, track_id))
            self._track_map[(camera_id, track_id)] = key
        return st

    def _apply(self, ev: Event) -> Optional[EntityState]:
        matching = [s for s in self.cfg.sources if source_matches(s, ev)]
        plate = ev.details.get("plate") if ev.type == PLATE_RECOGNIZED else None
        if not matching and not (plate and self.cfg.merge_by_plate):
            return None
        st = self._entity_for(ev.camera_id, ev.track_id)
        if plate and self.cfg.merge_by_plate:
            st = self._attach_plate(st, plate, ev)
        if st.object_class == "unknown" and ev.object_class:
            st.object_class = ev.object_class
        st.camera_id, st.track_id = ev.camera_id, ev.track_id
        st.last_bbox, st.last_frame_id = tuple(ev.bbox), ev.frame_id
        st.last_activity = max(st.last_activity, ev.timestamp)
        for src in matching:
            self._add_contribution(st, src, ev)
        return st

    @staticmethod
    def _discriminator(ev: Event) -> str:
        parts = [ev.rule_id or ev.type]
        bindings = ev.details.get("bindings") or {}
        if "zone_id" in bindings:
            parts.append(str(bindings["zone_id"]))
        if ev.details.get("entry_id") is not None:
            parts.append(str(ev.details["entry_id"]))
        return ":".join(parts)

    def _add_contribution(self, st: EntityState, src: Source, ev: Event) -> None:
        points = src.points if isinstance(src.points, int) else int(ev.details.get("points", 0))
        if src.status_multiplier:
            points = int(round(points * src.status_multiplier.get(ev.details.get("status"), 1.0)))
        if points <= 0:
            return
        disc = self._discriminator(ev)
        bucket = st.contributions.setdefault(src.id, {})
        old = bucket.get(disc)
        bucket[disc] = Contribution(
            kind=src.id, label=src.label, points=max(points, old.points if old else 0),
            at=max(ev.timestamp, old.at if old else 0.0), event_type=ev.type, event_id=ev.event_id,
            discriminator=disc, reasons=list(ev.details.get("reasons") or [src.label]),
            camera_id=ev.camera_id, track_id=ev.track_id)

    # ------------------------------------------------------------------ merging by plate
    def _attach_plate(self, st: EntityState, plate: str, ev: Event) -> EntityState:
        scope = ev.camera_id if self.cfg.merge_scope == "camera" else "*"
        key = ("plate", scope, plate)
        if st.key == key:
            return st
        target = self._entities.get(key)
        if target is None:
            target = self._entities[key] = EntityState(key, st.camera_id, st.track_id)
        target.plate = plate

        if st.plate is None:                                   # a track-level entity: absorb it entirely
            self._absorb(target, st)
            for tk, ek in list(self._track_map.items()):
                if ek == st.key:
                    self._track_map[tk] = key
            self._entities.pop(st.key, None)
            self.stats["merges"] += 1
        else:                                                  # the plate changed: only this track moves
            self._track_map[(ev.camera_id, ev.track_id)] = key
            self.stats["plate_changed"] += 1
        return target

    @staticmethod
    def _absorb(target: EntityState, st: EntityState) -> None:
        for kind, bucket in st.contributions.items():
            tb = target.contributions.setdefault(kind, {})
            for disc, c in bucket.items():
                old = tb.get(disc)
                if old is None or (c.points, c.at) > (old.points, old.at):
                    tb[disc] = c
        target.last_activity = max(target.last_activity, st.last_activity)
        if target.object_class == "unknown":
            target.object_class = st.object_class
        if st.last_activity >= target.last_activity:
            target.last_bbox, target.last_frame_id = st.last_bbox, st.last_frame_id
        ranks = [LEVEL_RANK[x] for x in (target.alerted_level, st.alerted_level) if x]
        target.alerted_level = next((n for n, r in LEVEL_RANK.items() if ranks and r == max(ranks)), None)
        times = [t for t in (target.last_alert_ts, st.last_alert_ts) if t is not None]
        target.last_alert_ts = max(times) if times else None
