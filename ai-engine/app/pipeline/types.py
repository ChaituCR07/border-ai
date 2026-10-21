from dataclasses import dataclass
from dataclasses import field
from typing import Dict, List, Optional, Tuple

from app.schemas.events import Event
from app.schemas.tracking import FrameTracks
from app.tracking.track_store import StoreSnapshot
from ingestion.frame import Frame


@dataclass
class FrameResult:
    """Everything the output thread needs to draw one frame. Contains copies/snapshots
    only, so the inference thread can keep going without racing the renderer."""
    frame: Frame
    ft: FrameTracks
    events: List[Event]
    store: StoreSnapshot
    rule_stats: dict
    video_s: Optional[float]        # clip time for offline file sources, else None
    n_active: int
    n_lost: int
    plates: Dict[int, str] = field(default_factory=dict)
    flags: Dict[int, str] = field(default_factory=dict)       # track_id -> watchlist flag text
    threat: Dict[int, Tuple[int, str]] = field(default_factory=dict)
