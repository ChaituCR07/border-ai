from dataclasses import dataclass

import cv2
import numpy as np

from app.anpr.config import QualityConfig
from app.anpr.types import PlateBox

MODES = ("none", "gray", "clahe", "sharpen")


@dataclass
class PlateQuality:
    width: int
    height: int
    sharpness: float
    score: float          # 0-1, used as a voting weight
    ok: bool
    reason: str = ""


def crop_with_pad(image: np.ndarray, box: PlateBox, pad: float = 0.1) -> np.ndarray:
    h, w = image.shape[:2]
    bw, bh = box.x2 - box.x1, box.y2 - box.y1
    x1, y1 = max(0, int(box.x1 - pad * bw)), max(0, int(box.y1 - pad * bh))
    x2, y2 = min(w, int(box.x2 + pad * bw)), min(h, int(box.y2 + pad * bh))
    return image[y1:y2, x1:x2].copy()


def _normalized_gray(img: np.ndarray, height: int = 64) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    scale = height / h
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(gray, (max(1, int(round(w * scale))), height), interpolation=interp)


def plate_quality(img: np.ndarray, q: QualityConfig) -> PlateQuality:
    h, w = img.shape[:2]
    if h < 2 or w < 2:
        return PlateQuality(w, h, 0.0, 0.0, False, "empty")
    # Sharpness is measured at a fixed height so thresholds are comparable across crop sizes
    sharp = float(cv2.Laplacian(_normalized_gray(img), cv2.CV_64F).var())
    score = 0.6 * min(1.0, w / 120.0) + 0.4 * min(1.0, sharp / 150.0)
    if w < q.min_plate_width_px:
        return PlateQuality(w, h, sharp, score, False, "too_small")
    if h < q.min_plate_height_px:
        return PlateQuality(w, h, sharp, score, False, "too_short")
    if sharp < q.min_sharpness:
        return PlateQuality(w, h, sharp, score, False, "blurry")
    return PlateQuality(w, h, sharp, score, True)


def preprocess(img: np.ndarray, mode: str = "clahe", target_h: int = 96,
               border: int = 8) -> np.ndarray:
    """Resize to a fixed height, optionally enhance contrast, and add a border
    (text detectors work better with some context around the text). Returns BGR."""
    if mode not in MODES:
        raise ValueError(f"preprocess mode must be one of {MODES}, got {mode!r}")
    h, w = img.shape[:2]
    scale = target_h / h
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    out = cv2.resize(img, (max(1, int(round(w * scale))), target_h), interpolation=interp)

    if mode != "none":
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        if mode == "clahe":
            gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(gray)
        elif mode == "sharpen":
            blur = cv2.GaussianBlur(gray, (0, 0), 3)
            gray = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
        out = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    if border:
        out = cv2.copyMakeBorder(out, border, border, border, border, cv2.BORDER_REPLICATE)
    return out
