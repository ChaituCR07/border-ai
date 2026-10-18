from dataclasses import dataclass, field, fields, replace
from typing import List


def _build(cls, data):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass
class FaceConfig:
    enabled: bool = True
    engine: str = "opencv"
    detector_model: str = "face/face_detection_yunet_2023mar.onnx"
    recognizer_model: str = "face/face_recognition_sface_2021dec.onnx"
    insightface_pack: str = "buffalo_l"
    upper_fraction: float = 0.6
    detector_score: float = 0.8
    min_face_px: int = 40
    max_yaw_ratio: float = 0.5
    min_sharpness: float = 30.0
    every_n_frames: int = 5
    min_track_hits: int = 5
    max_reads_per_track: int = 15
    min_person_height_px: int = 120
    border_margin_px: int = 8
    min_embeddings: int = 3
    min_consistency: float = 0.75
    review_threshold: float = 0.45
    alert_threshold: float = 0.60
    allow_alert: bool = False
    min_margin: float = 0.05
    cooldown_s: float = 60.0
    gallery_refresh_s: float = 60.0

    def __post_init__(self):
        if self.engine not in ("opencv", "insightface", "scripted"):
            raise ValueError("face.engine must be opencv, insightface, or scripted")
        if not (-1.0 <= self.review_threshold <= 1.0 and -1.0 <= self.alert_threshold <= 1.0):
            raise ValueError("face thresholds must be cosine similarities between -1 and 1")
        if self.alert_threshold < self.review_threshold:
            raise ValueError("alert_threshold must be >= review_threshold")
        if self.every_n_frames < 1 or self.min_embeddings < 1 or self.max_reads_per_track < 1:
            raise ValueError("every_n_frames, min_embeddings, and max_reads_per_track must be >= 1")
        if not 0.1 <= self.upper_fraction <= 1.0:
            raise ValueError("upper_fraction must be between 0.1 and 1.0")


@dataclass
class ReidConfig:
    enabled: bool = True
    embedder: str = "color_layout"
    onnx_model: str = "reid/reid_model.onnx"
    onnx_input: List[int] = field(default_factory=lambda: [128, 256])
    every_n_frames: int = 15
    min_track_hits: int = 10
    max_samples_per_track: int = 8
    min_person_height_px: int = 96
    border_margin_px: int = 8
    min_samples: int = 3
    similarity_threshold: float = 0.90
    max_gap_s: float = 600.0
    allow_overlap: bool = True
    camera_pairs: List[List[str]] = field(default_factory=list)
    gallery_ttl_s: float = 900.0
    gallery_max_items: int = 2000
    max_queries: int = 2

    def __post_init__(self):
        if self.embedder not in ("color_layout", "onnx", "scripted"):
            raise ValueError("reid.embedder must be color_layout, onnx, or scripted")
        if not -1.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("reid.similarity_threshold must be between -1 and 1")
        if self.every_n_frames < 1 or self.min_samples < 1 or self.gallery_max_items < 1:
            raise ValueError("every_n_frames, min_samples, and gallery_max_items must be >= 1")


@dataclass
class IdentityConfig:
    enabled: bool = False
    person_classes: List[str] = field(default_factory=lambda: ["person"])
    max_jobs_per_frame: int = 4
    queue_size: int = 64
    save_crops: bool = False
    crop_margin: float = 0.05
    face: FaceConfig = field(default_factory=FaceConfig)
    reid: ReidConfig = field(default_factory=ReidConfig)

    @classmethod
    def from_config(cls, cfg: dict) -> "IdentityConfig":
        cfg = dict(cfg or {})
        nested = {"face": _build(FaceConfig, cfg.pop("face", None)),
                  "reid": _build(ReidConfig, cfg.pop("reid", None))}
        return replace(_build(cls, cfg), **nested)
