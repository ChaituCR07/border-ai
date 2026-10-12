from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from app.utils.timeutil import to_iso_utc


@dataclass
class PlateBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


@dataclass
class OcrResult:
    text: str
    confidence: float
    lines: List[Tuple[str, float]] = field(default_factory=list)


@dataclass
class PlateRead:
    """One OCR reading of one vehicle at one moment."""
    text: str                      # normalized/corrected text
    raw: str                       # what OCR actually returned
    confidence: float              # OCR confidence
    weight: float                  # voting weight (confidence x quality x format level)
    quality: float                 # 0-1 plate crop quality
    level: str                     # strict | loose | invalid
    frame_id: int
    timestamp: float
    crop: Optional[np.ndarray] = None


@dataclass
class PlateRecord:
    """The stored result per vehicle: your plan's {vehicle_id, plate, confidence} plus context."""
    camera_id: str
    track_id: int                  # = vehicle_id
    plate: str
    confidence: float
    reads: int
    votes: int
    agreement: float
    format_level: str
    final: bool
    vehicle_class: str
    first_seen: float
    last_seen: float
    method: str = "exact"
    read_log: List[Tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "vehicle_id": self.track_id,
            "plate": self.plate,
            "confidence": round(self.confidence, 3),
            "camera_id": self.camera_id,
            "vehicle_class": self.vehicle_class,
            "reads": self.reads,
            "votes": self.votes,
            "agreement": round(self.agreement, 3),
            "format": self.format_level,
            "final": self.final,
            "method": self.method,
            "first_seen": to_iso_utc(self.first_seen),
            "last_seen": to_iso_utc(self.last_seen),
        }
        if self.read_log:
            d["read_log"] = [[t, round(c, 3)] for t, c in self.read_log]
        return d
