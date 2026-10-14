from dataclasses import dataclass
from datetime import datetime
from typing import Optional

ENTITY_TYPES = ("VEHICLE", "PLATE", "PERSON", "FACE")
PLATE_TYPES = ("VEHICLE", "PLATE")                 # matched against recognized plates
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
RISK_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
STATUS_RANK = {"suppressed": 0, "review": 1, "alert": 2}


class WatchlistError(Exception):
    pass


class DuplicateEntry(WatchlistError):
    pass


class EntryNotFound(WatchlistError):
    pass


class InvalidEntry(WatchlistError):
    pass


class RepoUnavailable(WatchlistError):
    """The backing store cannot be reached (database down, pool timeout)."""


@dataclass
class WatchlistEntry:
    watchlist_id: int
    entity_type: str
    identifier: str
    normalized_identifier: str
    name: str
    description: str
    risk_level: str
    active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass
class WatchlistHit:
    watchlist_id: int
    camera_id: str
    track_id: int
    plate: str
    match_type: str                 # exact | near
    distance: float
    plate_confidence: float
    score: int
    status: str                     # alert | review | suppressed
    seen_at: datetime
    event_id: Optional[str] = None
