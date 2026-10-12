from pathlib import Path
from typing import List, Tuple

import numpy as np

from app.anpr.config import LocatorConfig
from app.anpr.types import PlateBox


def filter_boxes(boxes: List[PlateBox], shape: Tuple[int, ...], lc: LocatorConfig) -> List[PlateBox]:
    """Keep only boxes with a plate-like size and aspect ratio, best confidence first."""
    h, w = shape[:2]
    kept = []
    for b in boxes:
        bw, bh = b.x2 - b.x1, b.y2 - b.y1
        if bw <= 0 or bh <= 0:
            continue
        area_frac = (bw * bh) / float(h * w)
        aspect = bw / bh
        if lc.min_area_frac <= area_frac <= lc.max_area_frac and lc.min_aspect <= aspect <= lc.max_aspect:
            kept.append(b)
    return sorted(kept, key=lambda b: -b.confidence)


class YoloPlateLocator:
    """A pretrained or fine-tuned YOLO plate detector (single class), run on vehicle crops."""

    def __init__(self, weights: Path, lc: LocatorConfig, device: str = "auto"):
        from ultralytics import YOLO
        self.model = YOLO(str(weights))
        self.lc, self.device = lc, device
        self.locate(np.zeros((160, 320, 3), np.uint8))          # warm-up

    def locate(self, vehicle_crop: np.ndarray) -> List[PlateBox]:
        kwargs = dict(conf=self.lc.conf, imgsz=self.lc.imgsz, verbose=False)
        if self.device != "auto":
            kwargs["device"] = self.device
        res = self.model.predict(vehicle_crop, **kwargs)[0]
        boxes = []
        if res.boxes is not None and len(res.boxes):
            for (x1, y1, x2, y2), c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.conf.cpu().numpy()):
                boxes.append(PlateBox(float(x1), float(y1), float(x2), float(y2), float(c)))
        return filter_boxes(boxes, vehicle_crop.shape, self.lc)


class LowerRegionLocator:
    """Baseline with no plate model: treat the lower part of the vehicle as the plate region and
    let OCR's own text detection find the text. Junk reads are filtered by format and consensus.
    Plates sit low on most vehicles; this will be noisier than a real plate detector."""

    def __init__(self, top_frac: float = 0.5):
        self.top_frac = top_frac

    def locate(self, vehicle_crop: np.ndarray) -> List[PlateBox]:
        h, w = vehicle_crop.shape[:2]
        return [PlateBox(0.0, h * self.top_frac, float(w), float(h), 0.0)]
