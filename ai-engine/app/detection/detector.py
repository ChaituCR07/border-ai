import logging
import threading
import time
from typing import List, Optional, Sequence

import numpy as np
import torch
from ultralytics import YOLO

from app import config
from app.detection.classes import resolve_class_ids
from app.detection.inference import result_to_detections
from app.schemas.detection import Detection, FrameDetections

log = logging.getLogger("detector")


def resolve_device(requested: str) -> str:
    if requested and requested != "auto":
        return requested
    return "cuda:0" if torch.cuda.is_available() else "cpu"


class Detector:
    """Owns the model, class filter, thresholds, and device settings.

    - detect()          one image  -> list[Detection]
    - detect_batch()    N images   -> list[list[Detection]]
    - detect_frame()    one Frame  -> FrameDetections (JSON-ready)
    - detect_frames()   N Frames   -> list[FrameDetections]

    Thread-safe: one model instance is shared, so inference calls are serialized
    with a lock (the model is not safe to call from several threads at once).
    """

    def __init__(self, model_name: str = "yolov8n.pt", conf: float = 0.4,
                 iou: float = 0.5, imgsz: int = 640,
                 classes: Optional[List[str]] = None, device: str = "auto",
                 half: bool = False, max_det: int = 300):
        self.model_name = model_name
        self.conf, self.iou, self.imgsz, self.max_det = conf, iou, imgsz, max_det
        self.device = resolve_device(device)

        # FP16 only makes sense on CUDA. On CPU, fall back to FP32 instead of failing.
        self.half = bool(half) and self.device.startswith("cuda")
        if half and not self.half:
            log.warning("FP16 requested but device is %s; running FP32", self.device)

        local = config.MODEL_DIR / model_name
        self.model = YOLO(str(local) if local.exists() else model_name)
        self.class_names = list(classes) if classes else None
        self.class_ids = (resolve_class_ids(self.model.names, classes)
                          if classes else None)

        self._lock = threading.Lock()
        self.frames_processed = 0
        self.avg_ms_per_frame = 0.0            # exponential moving average

        self.warmup()
        log.info("Detector ready: model=%s device=%s half=%s imgsz=%d",
                 model_name, self.device, self.half, imgsz)

    # ---------- construction ----------
    @classmethod
    def from_config(cls, **overrides) -> "Detector":
        c = config.load_app_config()["model"]
        params = dict(model_name=c["name"], conf=c["confidence"], iou=c["iou"],
                      imgsz=c["image_size"], classes=c["classes"],
                      device=c.get("device", "auto"), half=c.get("half", False),
                      max_det=c.get("max_det", 300))
        params.update(overrides)
        return cls(**params)

    # ---------- core ----------
    def warmup(self, n: int = 2) -> None:
        """The first calls are always slow (CUDA init, kernel selection)."""
        dummy = np.zeros((self.imgsz, self.imgsz, 3), np.uint8)
        for _ in range(n):
            self._predict([dummy])
        self.frames_processed = 0
        self.avg_ms_per_frame = 0.0

    def _predict(self, images: Sequence[np.ndarray], conf: Optional[float] = None,
                 iou: Optional[float] = None):
        kwargs = dict(
            conf=self.conf if conf is None else conf,
            iou=self.iou if iou is None else iou,
            imgsz=self.imgsz, classes=self.class_ids, max_det=self.max_det,
            device=self.device, half=self.half, verbose=False)

        with self._lock:
            t0 = time.perf_counter()
            results = self.model.predict(list(images), **kwargs)
            batch = [result_to_detections(r) for r in results]
            if self.device.startswith("cuda"):
                torch.cuda.synchronize()
            elapsed_ms = (time.perf_counter() - t0) * 1000

        self._update_stats(len(images), elapsed_ms)
        return batch, elapsed_ms

    def _update_stats(self, n_frames: int, elapsed_ms: float) -> None:
        per_frame = elapsed_ms / max(n_frames, 1)
        alpha = 0.1
        self.avg_ms_per_frame = (per_frame if self.frames_processed == 0
                                 else (1 - alpha) * self.avg_ms_per_frame + alpha * per_frame)
        self.frames_processed += n_frames

    # ---------- public API ----------
    def detect(self, image: np.ndarray, conf: Optional[float] = None,
               iou: Optional[float] = None) -> List[Detection]:
        batch, _ = self._predict([image], conf, iou)
        return batch[0]

    def detect_batch(self, images: Sequence[np.ndarray], conf: Optional[float] = None,
                     iou: Optional[float] = None) -> List[List[Detection]]:
        if not images:
            return []
        batch, _ = self._predict(images, conf, iou)
        return batch

    def detect_frame(self, frame, conf: Optional[float] = None,
                     iou: Optional[float] = None) -> FrameDetections:
        return self.detect_frames([frame], conf, iou)[0]

    def detect_frames(self, frames: Sequence, conf: Optional[float] = None,
                      iou: Optional[float] = None) -> List[FrameDetections]:
        """Batch across cameras. `frames` are ingestion Frame objects."""
        if not frames:
            return []
        batch, elapsed_ms = self._predict([f.image for f in frames], conf, iou)
        per_frame_ms = elapsed_ms / len(frames)
        return [
            FrameDetections(
                camera_id=f.camera_id, frame_id=f.frame_id, timestamp=f.timestamp,
                width=f.image.shape[1], height=f.image.shape[0],
                detections=dets, inference_ms=per_frame_ms)
            for f, dets in zip(frames, batch)
        ]

    def info(self) -> dict:
        return {
            "model": self.model_name, "device": self.device, "half": self.half,
            "imgsz": self.imgsz, "conf": self.conf, "iou": self.iou,
            "classes": self.class_names, "max_det": self.max_det,
            "frames_processed": self.frames_processed,
            "avg_ms_per_frame": round(self.avg_ms_per_frame, 2),
        }
