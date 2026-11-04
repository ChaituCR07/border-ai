"""Tracker runner invoking production CameraTracker or evaluation fallback."""
import logging
from typing import Dict, List, Optional

from evaluation.datasets.base import Box, TrackingFrame, TrackingSequence
from evaluation.detection.metrics import compute_iou
from evaluation.tracking.mot_io import MotRow

log = logging.getLogger("eval.tracker")


class SimpleIoUTracker:
    """Fallback IoU tracker for environments where Ultralytics is not available."""

    def __init__(self, match_thresh: float = 0.5, max_lost: int = 30) -> None:
        self.match_thresh = match_thresh
        self.max_lost = max_lost
        self.next_id = 1
        # track_id -> (last_box, last_seen_frame)
        self.active_tracks: Dict[int, tuple] = {}

    def update(self, frame_idx: int, detections: List[MotRow]) -> List[MotRow]:
        # Drop stale tracks
        stale = [tid for tid, (b, f) in self.active_tracks.items() if frame_idx - f > self.max_lost]
        for tid in stale:
            del self.active_tracks[tid]

        matched_preds = set()
        matched_tracks = set()
        results: List[MotRow] = []

        # Greedy match on IoU
        candidates = []
        for p_idx, det in enumerate(detections):
            for tid, (last_box, _) in self.active_tracks.items():
                iou = compute_iou(det.box, last_box)
                if iou >= self.match_thresh:
                    candidates.append((iou, p_idx, tid))
        candidates.sort(key=lambda c: c[0], reverse=True)

        for iou, p_idx, tid in candidates:
            if p_idx in matched_preds or tid in matched_tracks:
                continue
            matched_preds.add(p_idx)
            matched_tracks.add(tid)
            det = detections[p_idx]
            self.active_tracks[tid] = (det.box, frame_idx)
            results.append(MotRow(frame=frame_idx, track_id=tid, box=det.box, conf=det.conf))

        # Start new tracks for unmatched detections
        for p_idx, det in enumerate(detections):
            if p_idx not in matched_preds:
                tid = self.next_id
                self.next_id += 1
                self.active_tracks[tid] = (det.box, frame_idx)
                results.append(MotRow(frame=frame_idx, track_id=tid, box=det.box, conf=det.conf))

        return results


def run_tracker_on_sequence(
    sequence: TrackingSequence,
    detections_by_frame: Optional[Dict[int, List[MotRow]]] = None,
    track_buffer: int = 30,
    match_thresh: float = 0.7,
) -> Dict[int, List[MotRow]]:
    """Runs tracking on a sequence and returns results organized by frame index."""
    fps = sequence.fps if sequence.fps > 0 else 30.0
    adjusted_buffer = max(1, int((fps / 30.0) * track_buffer))

    tracker = None
    try:
        from app.tracking.tracker import CameraTracker, TrackerParams
        params = TrackerParams(
            track_buffer=adjusted_buffer,
            match_thresh=match_thresh,
            track_high_thresh=0.5,
            track_low_thresh=0.1,
        )
        tracker = CameraTracker(
            camera_id=sequence.name,
            frame_rate=fps,
            params=params,
            class_names={0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"},
        )
    except Exception as e:
        log.info("Using evaluation SimpleIoUTracker fallback: %s", e)
        tracker = SimpleIoUTracker(match_thresh=match_thresh, max_lost=adjusted_buffer)

    results_by_frame: Dict[int, List[MotRow]] = {}

    for frame in sequence.frames():
        f_idx = frame.frame_index
        # Get frame detections (either supplied from detector or from GT if tracker-only evaluation)
        if detections_by_frame is not None:
            cur_dets = detections_by_frame.get(f_idx, [])
        else:
            # Tracker-only protocol: feed GT boxes with conf=0.9
            cur_dets = [
                MotRow(frame=f_idx, track_id=-1, box=g.box, conf=0.9)
                for g in frame.gt
                if not g.ignore
            ]

        if isinstance(tracker, SimpleIoUTracker):
            tracked_rows = tracker.update(f_idx, cur_dets)
        else:
            # Production tracker
            from app.schemas.detection import Detection, FrameDetections
            from app.schemas.geometry import BoundingBox
            dets_schema = [
                Detection(
                    bbox=BoundingBox(x=d.box.x, y=d.box.y, w=d.box.w, h=d.box.h),
                    confidence=d.conf,
                    label="person",
                    class_id=0,
                )
                for d in cur_dets
            ]
            fd = FrameDetections(
                camera_id=sequence.name,
                frame_number=f_idx,
                timestamp=frame.timestamp,
                width=sequence.width,
                height=sequence.height,
                detections=dets_schema,
            )
            tracked_objs = tracker.update(fd)
            tracked_rows = [
                MotRow(
                    frame=f_idx,
                    track_id=t.track_id,
                    box=Box(x=t.x1, y=t.y1, w=t.x2 - t.x1, h=t.y2 - t.y1),
                    conf=t.confidence,
                )
                for t in tracked_objs
            ]

        results_by_frame[f_idx] = tracked_rows

    return results_by_frame
