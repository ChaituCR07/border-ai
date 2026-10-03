from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from ultralytics import YOLO

from app import config
from app.schemas.detection import Detection


def load_model(name: str) -> YOLO:
    """Load weights from ai-engine/models if present, otherwise let Ultralytics fetch them."""
    local = config.MODEL_DIR / name
    model = YOLO(str(local) if local.exists() else name)
    # Warm-up: the first inference is always slow (CUDA init, kernel selection).
    # Never include it in timing numbers.
    model.predict(np.zeros((640, 640, 3), np.uint8), verbose=False)
    return model


def run_inference(model: YOLO, image: np.ndarray, conf: float, iou: float,
                  imgsz: int, class_ids: Optional[List[int]] = None,
                  device: str = "auto", max_det: int = 300
                  ) -> Tuple[List[Detection], dict]:
    """Run YOLO on one BGR image. Returns (detections, speed_ms_dict)."""
    kwargs = dict(conf=conf, iou=iou, imgsz=imgsz, classes=class_ids,
                  max_det=max_det, verbose=False)
    if device != "auto":
        kwargs["device"] = device

    result = model.predict(image, **kwargs)[0]

    detections: List[Detection] = []
    boxes = result.boxes
    if boxes is not None and len(boxes) > 0:
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        for (x1, y1, x2, y2), c, k in zip(xyxy, confs, classes):
            detections.append(Detection(
                class_id=int(k), class_name=result.names[int(k)],
                confidence=float(c),
                x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2)))
    return detections, result.speed
