import logging
import threading
import time
from typing import Optional

import cv2

from .base import VideoSource
from ..frame import Frame

log = logging.getLogger("ingestion.rtsp")


class RtspSource(VideoSource):
    def __init__(self, camera_id: str, url: str, target_fps: Optional[float] = None,
                 resize_width: Optional[int] = None,
                 reconnect_initial: float = 1.0, reconnect_max: float = 30.0):
        super().__init__(camera_id, target_fps, resize_width)
        self.url = url
        self.reconnect_initial = reconnect_initial
        self.reconnect_max = reconnect_max

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._latest = None          # newest decoded image
        self._latest_ts = 0.0        # wall-clock time it was decoded
        self._seq = 0                # increments per decoded frame
        self._last_returned_seq = 0
        self._connected = False
        self._last_emit = 0.0
        self._min_interval = (1.0 / target_fps) if target_fps else 0.0

    @property
    def is_live(self) -> bool:
        return True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_frame_age(self) -> float:
        """Seconds since the last decoded frame (large value = stream is stuck)."""
        return time.time() - self._latest_ts if self._latest_ts else float("inf")

    def open(self) -> bool:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._reader_loop, daemon=True, name=f"rtsp-{self.camera_id}")
        self._thread.start()
        return True  # connection happens (and retries) in the background

    def _reader_loop(self) -> None:
        backoff = self.reconnect_initial
        while not self._stop.is_set():
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                self._connected = False
                log.warning("[%s] cannot open stream, retrying in %.1fs",
                            self.camera_id, backoff)
                cap.release()
                self._stop.wait(backoff)
                backoff = min(backoff * 2, self.reconnect_max)
                continue

            log.info("[%s] stream connected", self.camera_id)
            backoff = self.reconnect_initial
            self._connected = True
            self.source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

            while not self._stop.is_set():
                ok, image = cap.read()
                if not ok:
                    break
                with self._lock:
                    self._latest = image
                    self._latest_ts = time.time()
                    self._seq += 1

            cap.release()
            self._connected = False
            if not self._stop.is_set():
                log.warning("[%s] stream lost, reconnecting in %.1fs",
                            self.camera_id, backoff)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, self.reconnect_max)

    def read(self) -> Optional[Frame]:
        # Throttle BEFORE consuming, so skipped frames are simply never handed out
        now = time.monotonic()
        if self._min_interval and (now - self._last_emit) < self._min_interval:
            return None

        with self._lock:
            if self._latest is None or self._seq == self._last_returned_seq:
                return None
            image = self._latest
            ts = self._latest_ts
            self._last_returned_seq = self._seq

        self._last_emit = now
        return self._make_frame(image, video_time_ms=0.0, timestamp=ts)

    def release(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)  # cap.read() can block; thread is a daemon
            self._thread = None
