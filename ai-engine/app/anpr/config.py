from dataclasses import dataclass, field, fields, replace
from typing import List


def _build(cls, data):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass
class LocatorConfig:
    type: str = "yolo"
    weights: str = "plate_detector.pt"
    conf: float = 0.4
    imgsz: int = 640
    min_aspect: float = 1.0
    max_aspect: float = 7.0
    min_area_frac: float = 0.002
    max_area_frac: float = 0.30


@dataclass
class OcrConfig:
    engine: str = "paddle"
    lang: str = "en"
    device: str = "cpu"
    url: str = "http://127.0.0.1:8100/ocr"
    min_confidence: float = 0.30


@dataclass
class ScheduleConfig:
    min_track_hits: int = 5
    ocr_every_n_frames: int = 5
    max_reads_per_track: int = 20
    min_vehicle_width_px: int = 90
    border_margin_px: int = 8
    crop_margin: float = 0.05


@dataclass
class QualityConfig:
    min_plate_width_px: int = 50
    min_plate_height_px: int = 15
    min_sharpness: float = 40.0


@dataclass
class ConsensusConfig:
    min_reads: int = 3
    stable_share: float = 0.6
    loose_weight: float = 0.6
    invalid_weight: float = 0.3
    final_min_confidence: float = 0.5


@dataclass
class AnprConfig:
    enabled: bool = True
    vehicle_classes: List[str] = field(default_factory=lambda: ["car", "truck", "bus", "motorcycle"])
    formats: List[str] = field(default_factory=lambda: ["indian", "generic"])
    preprocess: str = "clahe"
    preprocess_height: int = 96
    crop_pad: float = 0.10
    save_crops: bool = True
    keep_read_log: bool = True
    queue_size: int = 32
    locator: LocatorConfig = field(default_factory=LocatorConfig)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    consensus: ConsensusConfig = field(default_factory=ConsensusConfig)

    @classmethod
    def from_config(cls, cfg: dict) -> "AnprConfig":
        cfg = dict(cfg or {})
        nested = {
            "locator": _build(LocatorConfig, cfg.pop("locator", None)),
            "ocr": _build(OcrConfig, cfg.pop("ocr", None)),
            "schedule": _build(ScheduleConfig, cfg.pop("schedule", None)),
            "quality": _build(QualityConfig, cfg.pop("quality", None)),
            "consensus": _build(ConsensusConfig, cfg.pop("consensus", None)),
        }
        return replace(_build(cls, cfg), **nested)
