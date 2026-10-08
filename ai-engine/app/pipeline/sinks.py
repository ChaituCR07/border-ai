import json
import logging
import threading
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("pipeline.sinks")


class JsonlSink:
    """Append-only JSON Lines file (line-buffered) plus an in-memory ring of recent records."""

    def __init__(self, path: Path, keep_recent: int = 200):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(self.path, "w", buffering=1)
        self._lock = threading.Lock()
        self._recent: Deque[dict] = deque(maxlen=keep_recent)
        self.count = 0

    def write(self, record: dict) -> None:
        line = json.dumps(record)
        with self._lock:
            if self._f.closed:
                return
            self._f.write(line + "\n")
            self._recent.append(record)
            self.count += 1

    def recent_records(self, limit: int = 50, camera_id: Optional[str] = None) -> List[dict]:
        with self._lock:
            items = list(self._recent)
        if camera_id:
            items = [r for r in items if r.get("camera_id") == camera_id]
        return items[-limit:][::-1]                      # newest first

    def close(self) -> None:
        with self._lock:
            if not self._f.closed:
                self._f.close()


class VideoSink:
    """MP4 writer created on the first frame. Later frames of a different size are
    resized to the first frame's size (an RTSP reconnect can change resolution)."""

    def __init__(self, path: Path, fps: float, fourcc: str = "mp4v"):
        self.path = Path(path)
        self.fps = max(1.0, float(fps))
        self.fourcc = fourcc
        self.frames = 0
        self._writer = None
        self._size: Optional[Tuple[int, int]] = None

    def write(self, image: np.ndarray) -> None:
        if self._writer is None:
            h, w = image.shape[:2]
            self._size = (w, h)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._writer = cv2.VideoWriter(str(self.path),
                                           cv2.VideoWriter_fourcc(*self.fourcc),
                                           self.fps, self._size)
            if not self._writer.isOpened():
                raise RuntimeError(f"Cannot open video writer for {self.path}")
        if (image.shape[1], image.shape[0]) != self._size:
            image = cv2.resize(image, self._size)
        self._writer.write(image)
        self.frames += 1

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None


class FrameHub:
    """Latest annotated frame per camera. JPEG encoding happens lazily, only when a
    viewer (HTTP request or display) asks, and is cached per frame sequence number.
    Stored images must not be modified after put()."""

    def __init__(self, jpeg_quality: int = 80):
        self.quality = jpeg_quality
        self._cond = threading.Condition()
        self._latest: Dict[str, Tuple[int, np.ndarray]] = {}
        self._jpeg: Dict[str, Tuple[int, bytes]] = {}

    def put(self, camera_id: str, image: np.ndarray) -> None:
        with self._cond:
            seq = self._latest[camera_id][0] + 1 if camera_id in self._latest else 1
            self._latest[camera_id] = (seq, image)
            self._cond.notify_all()

    def seq(self, camera_id: str) -> int:
        with self._cond:
            return self._latest[camera_id][0] if camera_id in self._latest else 0

    def latest_image(self, camera_id: str) -> Optional[np.ndarray]:
        with self._cond:
            item = self._latest.get(camera_id)
        return item[1] if item else None

    def wait_for_new(self, camera_id: str, last_seq: int, timeout: float):
        """Block until a frame newer than last_seq exists. Returns (seq, image) or (None, None)."""
        with self._cond:
            self._cond.wait_for(
                lambda: camera_id in self._latest and self._latest[camera_id][0] > last_seq,
                timeout=timeout)
            item = self._latest.get(camera_id)
            if item is None or item[0] <= last_seq:
                return None, None
            return item

    def jpeg(self, camera_id: str, seq: int, image: np.ndarray) -> bytes:
        cached = self._jpeg.get(camera_id)
        if cached and cached[0] == seq:
            return cached[1]
        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        data = buf.tobytes() if ok else b""
        self._jpeg[camera_id] = (seq, data)
        return data
