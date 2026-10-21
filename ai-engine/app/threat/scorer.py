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
