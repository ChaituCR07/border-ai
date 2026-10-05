from typing import Dict, Optional, Tuple

from app.schemas.detection import FrameDetections
from app.schemas.tracking import FrameTracks
from app.tracking.track_store import TrackStore, TrackUpdate
from app.tracking.tracker import CameraTracker, TrackerParams


class MultiCameraTracker:
    """Owns one CameraTracker + TrackStore per camera, created lazily.
    Call from a single thread, feeding each camera's frames in order."""

    def __init__(self, class_names: Dict[int, str], params: TrackerParams,
                 default_fps: float = 15.0, camera_fps: Optional[Dict[str, float]] = None):
        self.names = class_names
        self.params = params
        self.default_fps = default_fps
        self.camera_fps = camera_fps or {}
        self._trackers: Dict[str, CameraTracker] = {}
        self._stores: Dict[str, TrackStore] = {}

    def _ensure(self, camera_id: str) -> None:
        if camera_id in self._trackers:
            return
        fps = self.camera_fps.get(camera_id, self.default_fps)
        self._trackers[camera_id] = CameraTracker(camera_id, fps, self.params, self.names)
        self._stores[camera_id] = TrackStore(
            camera_id, self.params.max_lost_frames(fps), self.params.trail_length)

    def update(self, fd: FrameDetections,
               timestamp: Optional[float] = None) -> Tuple[FrameTracks, TrackUpdate]:
        """`timestamp` overrides fd.timestamp. Use video time for offline clips
        (see Challenges: wall-clock time is wrong when a clip is processed faster than real time)."""
        self._ensure(fd.camera_id)
        ts = fd.timestamp if timestamp is None else timestamp
        tracked = self._trackers[fd.camera_id].update(fd)
        upd = self._stores[fd.camera_id].update(tracked, ts)
        ft = FrameTracks(fd.camera_id, fd.frame_id, ts, fd.width, fd.height,
                         tracked, fd.inference_ms)
        return ft, upd

    def store(self, camera_id: str) -> TrackStore:
        self._ensure(camera_id)
        return self._stores[camera_id]

    def drop_camera(self, camera_id: str) -> None:
        """Discard a camera's state. A re-added camera starts fresh.
        (Do not call the underlying tracker's reset(): see Challenges.)"""
        self._trackers.pop(camera_id, None)
        self._stores.pop(camera_id, None)
