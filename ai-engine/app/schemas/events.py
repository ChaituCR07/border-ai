import uuid
from dataclasses import dataclass, field
from typing import Optional, Tuple

from app.utils.timeutil import to_iso_utc

ZONE_ENTER = "ZONE_ENTER"
ZONE_EXIT = "ZONE_EXIT"
ZONE_DWELL = "ZONE_DWELL"
LOITERING = "LOITERING"
LINE_CROSSING = "LINE_CROSSING"


@dataclass
class Event:
    type: str
    camera_id: str
    timestamp: float                      # epoch seconds (see the clock notes)
    frame_id: int
    track_id: int
    object_class: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    rule_id: str
    rule_name: str
    rule_kind: str                        # "zone" | "line"
    rule_type: str                        # from config: restricted, monitored, tripwire, ...
    direction: Optional[str] = None       # "IN" | "OUT" for line crossings
    dwell_s: Optional[float] = None
    details: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "type": self.type,
            "camera_id": self.camera_id,
            "timestamp": to_iso_utc(self.timestamp),
            "frame_id": self.frame_id,
            "track_id": self.track_id,
            "object": {
                "class": self.object_class,
                "confidence": round(self.confidence, 3),
                "bbox": [round(v, 1) for v in self.bbox],
            },
            "rule": {"id": self.rule_id, "name": self.rule_name,
                     "kind": self.rule_kind, "type": self.rule_type},
            "direction": self.direction,
            "dwell_s": None if self.dwell_s is None else round(self.dwell_s, 1),
            "details": self.details,
        }


def event_for(type, rule, rule_kind, ft, track_id, object_class, confidence, bbox, **kw) -> Event:
    """Build an Event from a rule (ZoneRule/LineRule) and the current FrameTracks."""
    return Event(type=type, camera_id=ft.camera_id, timestamp=ft.timestamp,
                 frame_id=ft.frame_id, track_id=track_id, object_class=object_class,
                 confidence=confidence, bbox=tuple(bbox), rule_id=rule.id,
                 rule_name=rule.name, rule_kind=rule_kind, rule_type=rule.type, **kw)
