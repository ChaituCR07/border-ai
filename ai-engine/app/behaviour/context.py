from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from app.schemas.events import (LINE_CROSSING, PLATE_RECOGNIZED, WATCHLIST_MATCH, ZONE_ENTER, ZONE_EXIT, Event)
from app.watchlist.models import RISK_RANK, STATUS_RANK


@dataclass
class ZonePresence:
    zone_id: str
    zone_type: str
    zone_name: str
    entered_at: float


class TrackContext:
    def __init__(self, camera_id: str, track_id: int):
        self.camera_id = camera_id
        self.track_id = track_id
        self.object_class = "unknown"
        self.first_seen = 0.0
        self.last_touch = 0.0
        self.zones: Dict[str, ZonePresence] = {}
        self.events: Deque[dict] = deque(maxlen=50)           # recent observation events, oldest first
        self.plate: Optional[str] = None
        self.plate_final = False
        self.watchlist: Optional[dict] = None                 # the strongest hit so far

    def touch(self, label: str, now: float) -> None:
        self.object_class = label
        if self.first_seen == 0.0:
            self.first_seen = now
        self.last_touch = max(self.last_touch, now)

    def ingest(self, ev: Event) -> None:
        """Fold one observation event into the context. Behaviour events are never ingested."""
        if ev.rule_kind == "behaviour":
            return
        self.last_touch = max(self.last_touch, ev.timestamp)
        if self.object_class == "unknown" and ev.object_class:
            self.object_class = ev.object_class

        if ev.type == ZONE_ENTER:
            self.zones[ev.rule_id] = ZonePresence(ev.rule_id, ev.rule_type, ev.rule_name, ev.timestamp)
        elif ev.type == ZONE_EXIT:
            self.zones.pop(ev.rule_id, None)
        elif ev.type == PLATE_RECOGNIZED:
            self.plate = ev.details.get("plate") or self.plate
            self.plate_final = bool(ev.details.get("final", False))
        elif ev.type == WATCHLIST_MATCH:
            hit = {"status": ev.details.get("status", "review"), "risk_level": ev.details.get("risk_level", "LOW"),
                   "entity_type": ev.details.get("entity_type", ""), "basis": ev.details.get("match_basis", "plate")}
            if self.watchlist is None or (STATUS_RANK[hit["status"]], RISK_RANK[hit["risk_level"]]) > \
                    (STATUS_RANK[self.watchlist["status"]], RISK_RANK[self.watchlist["risk_level"]]):
                self.watchlist = hit

        self.events.append({"type": ev.type, "ts": ev.timestamp, "rule_id": ev.rule_id,
                            "rule_type": ev.rule_type, "direction": ev.direction,
                            "status": ev.details.get("status"), "entity_type": ev.details.get("entity_type")})
