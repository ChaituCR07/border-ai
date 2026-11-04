"""Diagnostic analysis and root cause classification for ID switches."""
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from evaluation.datasets.base import Box, GtObject
from evaluation.detection.metrics import compute_iou
from evaluation.tracking.mot_io import MotRow


@dataclass
class IdSwitchIncident:
    frame: int
    gt_id: int
    old_pred_id: int
    new_pred_id: int
    cause: str
    details: str


def classify_id_switches(
    gt_frames: Dict[int, List[GtObject]],
    pred_frames: Dict[int, List[MotRow]],
    iou_thresh: float = 0.5,
) -> Tuple[List[IdSwitchIncident], Dict[str, int]]:
    """Analyzes and classifies identity switch incidents in tracking output."""
    all_frames = sorted(set(gt_frames.keys()) | set(pred_frames.keys()))

    last_gt_to_pred: Dict[int, int] = {}
    last_gt_seen_frame: Dict[int, int] = {}
    last_box_per_pred: Dict[int, Box] = {}

    incidents: List[IdSwitchIncident] = []
    cause_counts = {
        "occlusion": 0,
        "dropout": 0,
        "aspect_flicker": 0,
        "velocity_jump": 0,
        "unknown": 0,
    }

    for frame_idx in all_frames:
        gts = [g for g in gt_frames.get(frame_idx, []) if not g.ignore and g.track_id is not None]
        preds = pred_frames.get(frame_idx, [])

        matched_gt: set = set()
        matched_pred: set = set()

        # Match preds to GTs
        candidates = []
        for p_idx, p in enumerate(preds):
            for g_idx, g in enumerate(gts):
                iou = compute_iou(p.box, g.box)
                if iou >= iou_thresh:
                    candidates.append((iou, p_idx, g_idx))
        candidates.sort(key=lambda c: c[0], reverse=True)

        for _, p_idx, g_idx in candidates:
            if p_idx in matched_pred or g_idx in matched_gt:
                continue
            matched_pred.add(p_idx)
            matched_gt.add(g_idx)

            p = preds[p_idx]
            g = gts[g_idx]
            gid = g.track_id
            pid = p.track_id
            assert gid is not None

            # Detect ID switch
            if gid in last_gt_to_pred and last_gt_to_pred[gid] != pid:
                old_pid = last_gt_to_pred[gid]
                prev_frame = last_gt_seen_frame.get(gid, frame_idx - 1)
                frames_missed = frame_idx - prev_frame - 1

                cause = "unknown"
                details = ""

                # Check 1: Detection Dropout (>2 missed frames)
                if frames_missed >= 2:
                    cause = "dropout"
                    details = f"Lost for {frames_missed} frames before resuming under ID {pid}"

                # Check 2: Occlusion (proximity with other active tracks in frame)
                elif len(preds) > 1:
                    close_neighbors = 0
                    p_cx = p.box.x + p.box.w / 2.0
                    p_cy = p.box.y + p.box.h / 2.0
                    for other_p in preds:
                        if other_p.track_id == pid:
                            continue
                        o_cx = other_p.box.x + other_p.box.w / 2.0
                        o_cy = other_p.box.y + other_p.box.h / 2.0
                        dist = math.hypot(p_cx - o_cx, p_cy - o_cy)
                        if dist < 60.0:
                            close_neighbors += 1
                    if close_neighbors > 0:
                        cause = "occlusion"
                        details = f"Nearby tracks within 60px ({close_neighbors} neighbors)"

                # Check 3: Aspect Ratio Flicker
                if cause == "unknown" and old_pid in last_box_per_pred:
                    old_b = last_box_per_pred[old_pid]
                    old_aspect = old_b.w / max(1.0, old_b.h)
                    new_aspect = p.box.w / max(1.0, p.box.h)
                    if old_aspect > 0 and (new_aspect / old_aspect > 2.0 or old_aspect / new_aspect > 2.0):
                        cause = "aspect_flicker"
                        details = f"Aspect ratio jumped from {old_aspect:.2f} to {new_aspect:.2f}"

                # Check 4: Velocity Jump
                if cause == "unknown" and old_pid in last_box_per_pred:
                    old_b = last_box_per_pred[old_pid]
                    dx = abs(p.box.x - old_b.x)
                    dy = abs(p.box.y - old_b.y)
                    if math.hypot(dx, dy) > 100.0:
                        cause = "velocity_jump"
                        details = f"Center displacement {math.hypot(dx, dy):.1f}px exceeds 100px"

                cause_counts[cause] += 1
                incidents.append(
                    IdSwitchIncident(
                        frame=frame_idx,
                        gt_id=gid,
                        old_pred_id=old_pid,
                        new_pred_id=pid,
                        cause=cause,
                        details=details,
                    )
                )

            last_gt_to_pred[gid] = pid
            last_gt_seen_frame[gid] = frame_idx
            last_box_per_pred[pid] = p.box

    return incidents, cause_counts
