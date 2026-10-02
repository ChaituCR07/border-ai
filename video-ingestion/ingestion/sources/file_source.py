import time
from pathlib import Path
from typing import Optional

import cv2

from .base import VideoSource
from ..frame import Frame


class FileSource(VideoSource):
    """Reads a video file as if it were a camera.

    realtime=True  -> paces output to target_fps (or the file's native FPS)
    realtime=False -> reads as fast as possible (useful for benchmarks and tests)
    loop=True      -> restarts at the end so a short clip behaves like a live feed
    """

    def __init__(self, camera_id: str, path, target_fps: Optional[float] = None,
                 resize_width: Optional[int] = None, loop: bool = False,
                 realtime: bool = True):
        super().__init__(camera_id, target_fps, resize_width)
        self.path = Path(path)
        self.loop = loop
        self.realtime = realtime
        self.cap: Optional[cv2.VideoCapture] = None
        self._step = 1
        self._ended = False
        self._next_deadline: Optional[float] = None

    @property
    def is_live(self) -> bool:
        return False

    @property
    def ended(self) -> bool:
        return self._ended

    def open(self) -> bool:
        if not self.path.exists():
            return False
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            return False
        self.source_fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        # Frame skipping: e.g. a 30 FPS file with target_fps=10 -> keep every 3rd frame
        if self.target_fps and self.target_fps < self.source_fps:
            self._step = max(1, round(self.source_fps / self.target_fps))
        self._ended = False
        return True

    def read(self) -> Optional[Frame]:
        if self.cap is None or self._ended:
            return None

        # Skip (step - 1) frames cheaply with grab(), which avoids a full decode-to-array
        for _ in range(self._step - 1):
            if not self.cap.grab():
                return self._on_end()

        ok, image = self.cap.read()
        if not ok:
            return self._on_end()

        video_time_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        self._pace()
        return self._make_frame(image, video_time_ms=video_time_ms)

    def _on_end(self) -> Optional[Frame]:
        if self.loop:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, image = self.cap.read()
            if ok:  # guard: an unreadable file must not loop forever
                self._pace()
                return self._make_frame(image, video_time_ms=0.0)
        self._ended = True
        return None

    def _pace(self) -> None:
        if not self.realtime:
            return
        effective_fps = self.target_fps or self.source_fps
        interval = 1.0 / effective_fps
        now = time.monotonic()
        if self._next_deadline is None:
            self._next_deadline = now
        if self._next_deadline > now:
            time.sleep(self._next_deadline - now)
        self._next_deadline = max(self._next_deadline, now) + interval

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
