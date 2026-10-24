from datetime import datetime, timezone
from typing import Optional

from app.schemas.events import Event

TRACK_SUMMARY = "TRACK_SUMMARY"


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def track_summary_event(track, camera_id: str, frame_id: int, min_hits: int) -> Optional[Event]:
    """One summary event for a finished (or still live at stream end) track. Flickers are skipped.
    Adapt the attribute names below to your Day 5 Track class."""
    if track.hits < min_hits:
        return None
    first, last = track.first_seen, track.last_seen
    return Event(
        type=TRACK_SUMMARY, camera_id=camera_id, timestamp=last, frame_id=frame_id, track_id=track.track_id,
        object_class=track.dominant_class, confidence=float(track.last_confidence), bbox=tuple(track.last_bbox),
        rule_id="TRACK", rule_name="Track summary", rule_kind="track", rule_type="summary",
        details={"first_seen": _iso(first), "last_seen": _iso(last), "duration_s": round(max(0.0, last - first), 2),
                 "hits": int(track.hits), "max_confidence": round(float(track.last_confidence), 3)})
