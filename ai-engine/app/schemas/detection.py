from dataclasses import dataclass
from typing import List

from app.utils.timeutil import to_iso_utc


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def bbox(self):
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self):
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def bottom_center(self):
        """Ground-contact point. Used for zone and line logic on Day 6."""
        return ((self.x1 + self.x2) / 2, self.y2)


@dataclass
class FrameDetections:
    """All detections for one frame of one camera. This is the unit the rest of
    the pipeline (tracking, zones, events) will consume."""
    camera_id: str
    frame_id: int
    timestamp: float                 # epoch seconds (UTC), from the Frame
    width: int
    height: int
    detections: List[Detection]
    inference_ms: float = 0.0        # per-frame model time (batch time / batch size)

    def to_dict(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "timestamp": to_iso_utc(self.timestamp),
            "frame_size": {"width": self.width, "height": self.height},
            "inference_ms": round(self.inference_ms, 2),
            "objects": [
                {
                    "class": d.class_name,
                    "class_id": d.class_id,
                    "confidence": round(d.confidence, 3),
                    "bbox": [round(v, 1) for v in d.bbox],   # [x1, y1, x2, y2] in pixels
                }
                for d in self.detections
            ],
        }
