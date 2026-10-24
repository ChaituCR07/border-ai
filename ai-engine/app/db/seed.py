import re


def strip_credentials(url: str) -> str:
    return re.sub(r"://[^/@\s]+@", "://", url)


def camera_row(cfg) -> dict:
    """The database row for a camera from configs/cameras.json (Day 2 CameraConfig). No credentials, ever."""
    rtsp = strip_credentials(cfg.source) if cfg.source_type == "rtsp" else None
    return {"camera_id": cfg.camera_id, "name": cfg.name or cfg.camera_id, "location": getattr(cfg, "location", "") or "",
            "rtsp_url": rtsp, "status": "ACTIVE" if cfg.enabled else "INACTIVE",
            "metadata": {"source_type": cfg.source_type, "target_fps": cfg.target_fps}}
