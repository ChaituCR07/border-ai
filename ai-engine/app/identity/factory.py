import logging
from typing import Optional

from app import config
from app.identity.config import FaceConfig, IdentityConfig, ReidConfig
from app.identity.face import InsightFaceEngine, OpenCvFaceEngine
from app.identity.gallery import FaceGallery
from app.identity.reid import ColorLayoutEmbedder, OnnxPersonEmbedder
from app.identity.service import IdentityService
from app.watchlist.repo import InMemoryWatchlistRepo

log = logging.getLogger("identity")


def build_face_engine(cfg: FaceConfig, device: str = "auto"):
    if cfg.engine == "opencv":
        det, rec = config.MODEL_DIR / cfg.detector_model, config.MODEL_DIR / cfg.recognizer_model
        if not det.exists() or not rec.exists():
            log.error("Face model files not found (%s, %s). Download them as described in the Day 10 notes.", det, rec)
            return None
        return OpenCvFaceEngine(det, rec, cfg.detector_score)
    if cfg.engine == "insightface":
        return InsightFaceEngine(cfg.insightface_pack, use_gpu=str(device).startswith("cuda"))
    raise ValueError(f"Unknown face engine: {cfg.engine}")


def build_embedder(cfg: ReidConfig):
    if cfg.embedder == "color_layout":
        return ColorLayoutEmbedder()
    if cfg.embedder == "onnx":
        path = config.MODEL_DIR / cfg.onnx_model
        if not path.exists():
            log.error("Re-ID model not found at %s; falling back to the color_layout baseline", path)
            return ColorLayoutEmbedder()
        return OnnxPersonEmbedder(path, tuple(cfg.onnx_input))
    raise ValueError(f"Unknown Re-ID embedder: {cfg.embedder}")


def build_identity(app_cfg: dict, watchlist=None, force: bool = False) -> Optional[IdentityService]:
    cfg = IdentityConfig.from_config(app_cfg.get("identity"))
    if not (cfg.enabled or force):
        return None
    log.warning("IDENTITY FEATURES ARE ENABLED (face matching / person Re-ID). Use only consenting "
                "subjects or permitted datasets, and treat every match as a lead for a human to check.")

    device = app_cfg.get("model", {}).get("device", "auto")
    engine = build_face_engine(cfg.face, device) if cfg.face.enabled else None
    embedder = build_embedder(cfg.reid) if cfg.reid.enabled else None

    gallery = None
    if engine is not None:
        repo = watchlist.repo if watchlist is not None else InMemoryWatchlistRepo()
        gallery = FaceGallery(repo, engine.model_name, cfg.face.gallery_refresh_s)
    recorder = watchlist.persist_hit if watchlist is not None else None
    return IdentityService(cfg, engine, embedder, gallery, recorder)
