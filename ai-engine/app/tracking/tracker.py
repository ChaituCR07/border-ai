from dataclasses import dataclass, fields
from types import SimpleNamespace
from typing import Dict, List

import numpy as np
from ultralytics.trackers.byte_tracker import BYTETracker

from app.schemas.detection import FrameDetections
from app.schemas.tracking import TrackedObject


@dataclass
class TrackerParams:
    detection_conf: float = 0.25
    track_high_thresh: float = 0.5
    track_low_thresh: float = 0.1
    new_track_thresh: float = 0.6
    track_buffer: int = 30
    match_thresh: float = 0.8
    fuse_score: bool = True
    trail_length: int = 40

    @classmethod
    def from_config(cls, cfg: dict) -> "TrackerParams":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in cfg.items() if k in known})

    def max_lost_frames(self, fps: float) -> int:
        """Mirrors the tracker's own rule: lost tracks are dropped after this many updates."""
        return max(1, int(int(round(fps)) / 30.0 * self.track_buffer))


class _DetResults:
    """The minimal object the Ultralytics tracker reads: conf, xywh, cls."""

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray):
        self.xyxy = np.asarray(xyxy, dtype=np.float32)
        self.conf = np.asarray(conf, dtype=np.float32)
        self.cls = np.asarray(cls, dtype=np.float32)
        if len(self.xyxy):
            self.xywh = np.stack([
                (self.xyxy[:, 0] + self.xyxy[:, 2]) / 2, (self.xyxy[:, 1] + self.xyxy[:, 3]) / 2,
                self.xyxy[:, 2] - self.xyxy[:, 0], self.xyxy[:, 3] - self.xyxy[:, 1]], axis=1).astype(np.float32)
        else:
            self.xywh = np.zeros((0, 4), np.float32)

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, index):
        return _DetResults(self.xyxy[index], self.conf[index], self.cls[index])


class CameraTracker:
    """ByteTrack for ONE camera. Never share an instance between cameras.
    Call update() on EVERY frame, even when there are no detections, so lost
    tracks age correctly. Not thread-safe: call from a single thread."""

    def __init__(self, camera_id: str, frame_rate: float, params: TrackerParams,
                 class_names: Dict[int, str]):
        self.camera_id = camera_id
        self.names = class_names
        max_lost = params.max_lost_frames(frame_rate)
        args = SimpleNamespace(
            track_high_thresh=params.track_high_thresh,
            track_low_thresh=params.track_low_thresh,
            new_track_thresh=params.new_track_thresh,
            track_buffer=max_lost,
            match_thresh=params.match_thresh,
            fuse_score=params.fuse_score,
            frame_rate=int(round(frame_rate)),
        )
        self.tracker = BYTETracker(args)

    def update(self, fd: FrameDetections) -> List[TrackedObject]:
        dets = fd.detections
        if dets:
            xyxy = np.array([[d.x1, d.y1, d.x2, d.y2] for d in dets], np.float32)
            conf = np.array([d.confidence for d in dets], np.float32)
            cls = np.array([d.class_id for d in dets], np.float32)
        else:
            xyxy = np.zeros((0, 4), np.float32)
            conf = np.zeros((0,), np.float32)
            cls = np.zeros((0,), np.float32)

        out = self.tracker.update(_DetResults(xyxy, conf, cls))

        tracked: List[TrackedObject] = []
        if out is not None and np.size(out) > 0:
            for row in np.atleast_2d(out):
                x1, y1, x2, y2, tid, score, k = row[:7]
                # Kalman-predicted boxes can drift past the frame edge; clamp them
                x1, x2 = np.clip([x1, x2], 0, fd.width)
                y1, y2 = np.clip([y1, y2], 0, fd.height)
                tracked.append(TrackedObject(
                    track_id=int(tid), class_id=int(k),
                    class_name=self.names.get(int(k), str(int(k))),
                    confidence=float(score),
                    x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2)))
        return tracked
