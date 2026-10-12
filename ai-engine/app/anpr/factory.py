import logging
from typing import Optional

from app import config
from app.anpr.config import AnprConfig
from app.anpr.locator import LowerRegionLocator, YoloPlateLocator
from app.anpr.ocr import HttpOcrEngine, OcrEngine, PaddleOcrEngine, ScriptedOcrEngine
from app.anpr.service import AnprService

log = logging.getLogger("anpr")


def build_locator(cfg: AnprConfig, device: str = "auto"):
    lc = cfg.locator
    if lc.type == "yolo":
        weights = config.MODEL_DIR / lc.weights
        if weights.exists():
            return YoloPlateLocator(weights, lc, device)
        log.warning("Plate detector weights not found at %s; using the lower_region fallback", weights)
    return LowerRegionLocator()


def build_ocr(cfg: AnprConfig) -> OcrEngine:
    oc = cfg.ocr
    if oc.engine == "paddle":
        return PaddleOcrEngine(oc.lang, oc.device)
    if oc.engine == "http":
        return HttpOcrEngine(oc.url)
    if oc.engine == "fake":
        return ScriptedOcrEngine(["KA01AB1234"])
    raise ValueError(f"Unknown OCR engine: {oc.engine}")


def build_anpr(app_cfg: dict) -> Optional[AnprService]:
    """Build the service from configs/app.yaml. Returns None when ANPR is disabled."""
    cfg = AnprConfig.from_config(app_cfg.get("anpr"))
    if not cfg.enabled:
        return None
    device = app_cfg.get("model", {}).get("device", "auto")
    return AnprService(cfg, build_locator(cfg, device), build_ocr(cfg))
