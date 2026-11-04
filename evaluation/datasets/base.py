from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Protocol, Tuple


@dataclass(frozen=True)
class Box:
    """Bounding box in absolute pixel coordinates (top-left x, y, width, height)."""
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    @property
    def area(self) -> float:
        return max(0.0, self.w) * max(0.0, self.h)

    @property
    def foot_point(self) -> Tuple[float, float]:
        """Returns the bottom-center coordinate (x + w/2, y + h)."""
        return self.x + (self.w / 2.0), self.y + self.h

    def to_tlbr(self) -> List[float]:
        return [self.x, self.y, self.x2, self.y2]

    def to_tlwh(self) -> List[float]:
        return [self.x, self.y, self.w, self.h]


@dataclass
class GtObject:
    """Ground truth annotation object."""
    cls: str
    box: Box
    track_id: Optional[int] = None
    ignore: bool = False
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredObject:
    """Detector predicted bounding box."""
    cls: str
    score: float
    box: Box


@dataclass
class DetSample:
    """Single image sample for detection evaluation."""
    image_id: str
    path: str
    width: int
    height: int
    gt: List[GtObject]
    meta: Dict[str, Any] = field(default_factory=dict)


class DetectionDataset(Protocol):
    name: str

    def __iter__(self) -> Iterator[DetSample]: ...
    def __len__(self) -> int: ...


@dataclass
class TrackingFrame:
    frame_index: int  # 1-based index (MOT format)
    timestamp: float
    image_path: str
    gt: List[GtObject]


class TrackingSequence(Protocol):
    name: str
    fps: float
    width: int
    height: int
    is_static_camera: bool

    def frames(self) -> Iterator[TrackingFrame]: ...
    def __len__(self) -> int: ...


class TrackingDataset(Protocol):
    name: str

    def sequences(self) -> Iterator[TrackingSequence]: ...
    def __len__(self) -> int: ...
