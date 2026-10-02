import json
import logging
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .frame import Frame
from .sources.base import VideoSource
from .sources.file_source import FileSource
from .sources.rtsp_source import RtspSource

log = logging.getLogger("ingestion.manager")


class FpsCounter:
    """Rolling FPS over the last `window` frames."""

    def __init__(self, window: int = 30):
        self._ts = deque(maxlen=window)

    def tick(self) -> None:
        self._ts.append(time.monotonic())

    @property
    def fps(self) -> float:
        if len(self._ts) < 2:
            return 0.0
        span = self._ts[-1] - self._ts[0]
        return (len(self._ts) - 1) / span if span > 0 else 0.0


@dataclass
class CameraConfig:
    camera_id: str
    name: str
    source_type: str          # "file" | "rtsp"
    source: str
    target_fps: Optional[float] = None
    resize_width: Optional[int] = None
    loop: bool = False
    realtime: bool = True
    enabled: bool = True


def load_camera_configs(path: Path) -> List[CameraConfig]:
    with open(path, "r") as f:
        raw = json.load(f)
    configs = []
    for item in raw["cameras"]:
        item = dict(item)
        item["source"] = os.path.expandvars(item["source"])
        configs.append(CameraConfig(**item))
    ids = [c.camera_id for c in configs]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate camera_id in cameras.json")
    return configs


def build_source(cfg: CameraConfig, base_dir: Path) -> VideoSource:
    if cfg.source_type == "file":
        return FileSource(cfg.camera_id, base_dir / cfg.source,
                          target_fps=cfg.target_fps, resize_width=cfg.resize_width,
                          loop=cfg.loop, realtime=cfg.realtime)
    if cfg.source_type == "rtsp":
        return RtspSource(cfg.camera_id, cfg.source,
                          target_fps=cfg.target_fps, resize_width=cfg.resize_width)
    raise ValueError(f"Unknown source_type: {cfg.source_type}")


class CameraWorker(threading.Thread):
    """One thread per camera. Keeps a small bounded queue; when full, the OLDEST
    frame is dropped so latency never grows."""

    def __init__(self, source: VideoSource, queue_size: int = 2):
        super().__init__(daemon=True, name=f"cam-{source.camera_id}")
        self.source = source
        self.frames: "queue.Queue[Frame]" = queue.Queue(maxsize=queue_size)
        self.fps = FpsCounter()
        self.status = "starting"     # starting | running | reconnecting | ended | failed
        self.dropped = 0
        self.total = 0
        self._stop_evt = threading.Event()

    def run(self) -> None:
        if not self.source.open():
            self.status = "failed"
            log.error("[%s] failed to open source", self.source.camera_id)
            return

        while not self._stop_evt.is_set():
            frame = self.source.read()
            if frame is None:
                if self.source.ended:
                    self.status = "ended"
                    break
                self.status = "running" if self.source.connected else "reconnecting"
                time.sleep(0.005)
                continue

            self.status = "running"
            self.total += 1
            self.fps.tick()
            try:
                self.frames.put_nowait(frame)
            except queue.Full:
                try:
                    self.frames.get_nowait()   # drop the oldest
                except queue.Empty:
                    pass
                self.dropped += 1
                self.frames.put_nowait(frame)

        self.source.release()

    def get(self, timeout: float = 0.05) -> Optional[Frame]:
        try:
            return self.frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        self._stop_evt.set()


class CameraManager:
    def __init__(self, sources: List[VideoSource], queue_size: int = 2):
        self.workers: Dict[str, CameraWorker] = {
            s.camera_id: CameraWorker(s, queue_size) for s in sources
        }

    @classmethod
    def from_config(cls, config_path: Path, base_dir: Path) -> "CameraManager":
        configs = [c for c in load_camera_configs(config_path) if c.enabled]
        return cls([build_source(c, base_dir) for c in configs])

    def start_all(self) -> None:
        for w in self.workers.values():
            w.start()

    def stop_all(self) -> None:
        for w in self.workers.values():
            w.stop()
        for w in self.workers.values():
            w.join(timeout=5)

    @property
    def camera_ids(self) -> List[str]:
        return list(self.workers.keys())

    def get_frame(self, camera_id: str, timeout: float = 0.05) -> Optional[Frame]:
        return self.workers[camera_id].get(timeout)

    def stats(self) -> Dict[str, dict]:
        return {
            cid: {
                "status": w.status,
                "fps": round(w.fps.fps, 1),
                "frames": w.total,
                "dropped": w.dropped,
            }
            for cid, w in self.workers.items()
        }
