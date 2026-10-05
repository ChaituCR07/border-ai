from dataclasses import dataclass
from typing import List, Optional

from app.utils.timeutil import to_iso_utc


@dataclass
class TrackedObject:
    """One tracked object in one frame."""
    track_id: int
    class_id: int
    class_name: str                      # instantaneous class from this frame's detection
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    stable_class: Optional[str] = None   # majority-vote class (filled by TrackStore)
    age_s: float = 0.0                   # seconds since the track was first seen

    @property
    def bbox(self):
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def center(self):
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def bottom_center(self):
        """Ground-contact point. Used for trails now and for zones/lines on Day 6."""
        return ((self.x1 + self.x2) / 2, self.y2)

    @property
    def label(self) -> str:
        return self.stable_class or self.class_name


@dataclass
class FrameTracks:
    camera_id: str
    frame_id: int
    timestamp: float
    width: int
    height: int
    tracks: List[TrackedObject]
    inference_ms: float = 0.0

    def to_dict(self) -> dict:
        """Same shape as the Day 4 detection contract, plus track fields."""
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "timestamp": to_iso_utc(self.timestamp),
            "frame_size": {"width": self.width, "height": self.height},
            "inference_ms": round(self.inference_ms, 2),
            "objects": [
                {
                    "track_id": o.track_id,
                    "class": o.label,                       # majority-vote class
                    "confidence": round(o.confidence, 3),
                    "bbox": [round(v, 1) for v in o.bbox],
                    "age_s": round(o.age_s, 1),
                }
                for o in self.tracks
            ],
        }
