from abc import ABC, abstractmethod
from typing import Optional
import time

import cv2

from ..frame import Frame


def resize_keep_aspect(image, width: Optional[int]):
    """Downscale to `width` keeping aspect ratio. Never upscales."""
    if width is None:
        return image
    h, w = image.shape[:2]
    if w <= width:
        return image
    scale = width / w
    return cv2.resize(image, (width, int(h * scale)), interpolation=cv2.INTER_AREA)


class VideoSource(ABC):
    """Common interface for file and live sources."""

    def __init__(self, camera_id: str, target_fps: Optional[float] = None,
                 resize_width: Optional[int] = None):
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.resize_width = resize_width
        self.source_fps: float = 0.0
        self._frame_counter = 0

    # --- lifecycle ---
    @abstractmethod
    def open(self) -> bool: ...

    @abstractmethod
    def read(self) -> Optional[Frame]:
        """Return the next Frame, or None if no frame is available right now."""

    @abstractmethod
    def release(self) -> None: ...

    # --- state ---
    @property
    @abstractmethod
    def is_live(self) -> bool: ...

    @property
    def ended(self) -> bool:
        """True only for finite sources (files) once the end is reached."""
        return False

    @property
    def connected(self) -> bool:
        return True

    # --- helpers ---
    def _make_frame(self, image, video_time_ms: float = 0.0,
                    timestamp: Optional[float] = None) -> Frame:
        image = resize_keep_aspect(image, self.resize_width)
        self._frame_counter += 1
        return Frame(
            camera_id=self.camera_id,
            frame_id=self._frame_counter,
            timestamp=timestamp if timestamp is not None else time.time(),
            video_time_ms=video_time_ms,
            image=image,
            source_fps=self.source_fps,
        )
