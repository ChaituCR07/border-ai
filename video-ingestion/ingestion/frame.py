from dataclasses import dataclass
import numpy as np


@dataclass
class Frame:
    camera_id: str
    frame_id: int            # increments per emitted frame, per camera
    timestamp: float         # wall-clock UTC epoch seconds when the frame was read
    video_time_ms: float     # position in the video file (0.0 for live streams)
    image: np.ndarray        # BGR image (H, W, 3)
    source_fps: float        # native FPS reported by the source

    @property
    def height(self) -> int:
        return self.image.shape[0]

    @property
    def width(self) -> int:
        return self.image.shape[1]
