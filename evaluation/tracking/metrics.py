"""Tracking evaluation metrics: CLEAR MOT, IDF1, HOTA, and operational continuity."""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from evaluation.datasets.base import Box, GtObject
from evaluation.detection.metrics import compute_iou
from evaluation.tracking.mot_io import MotRow


@dataclass
class TrackingMetrics:
    sequence_name: str
    num_frames: int
    num_gt_trajectories: int
    num_gt_boxes: int
    mota: float
    motp: float
    idf1: float
    idp: float
    idr: float
    idsw: int
    frag: int
    mostly_tracked: int
    partially_tracked: int
    mostly_lost: int
    false_tracks_per_1000_frames: float
    mean_track_continuity: float
    hota: float
    deta: float
    assa: float


def evaluate_tracking_sequence(
    gt_frames: Dict[int, List[GtObject]],
    pred_frames: Dict[int, List[MotRow]],
    sequence_name: str = "seq",
    iou_thresh: float = 0.5,
) -> TrackingMetrics:
    """Evaluates tracking performance on a sequence matching MOT challenge methodology."""
    all_frame_indices = sorted(set(gt_frames.keys()) | set(pred_frames.keys()))
    num_frames = max(len(all_frame_indices), 1)

    total_gt_boxes = 0
    gt_trajectories: Dict[int, List[int]] = {}  # gt_id -> list of frames where present
    pred_trajectories: Dict[int, List[int]] = {}  # pred_id -> list of frames where present

    # Map previous match: gt_id -> last matched pred_id
    last_gt_to_pred: Dict[int, int] = {}
    last_gt_seen_frame: Dict[int, int] = {}

    total_fp = 0
    total_fn = 0
    total_idsw = 0
    total_frag = 0
    iou_sum = 0.0
    matched_boxes_count = 0

    # ID metrics tracking
    gt_match_counts: Dict[Tuple[int, int], int] = {}  # (gt_id, pred_id) -> count of matches
    gt_total_per_id: Dict[int, int] = {}
    pred_total_per_id: Dict[int, int] = {}

    # Track continuity metrics
    matched_preds_all_time: Set[int] = set()
    gt_frames_tracked_count: Dict[int, int] = {}

    for frame_idx in all_frame_indices:
        gts = [g for g in gt_frames.get(frame_idx, []) if not g.ignore and g.track_id is not None]
        preds = pred_frames.get(frame_idx, [])

        total_gt_boxes += len(gts)
        for g in gts:
            assert g.track_id is not None
            gt_trajectories.setdefault(g.track_id, []).append(frame_idx)
            gt_total_per_id[g.track_id] = gt_total_per_id.get(g.track_id, 0) + 1

        for p in preds:
            pred_trajectories.setdefault(p.track_id, []).append(frame_idx)
            pred_total_per_id[p.track_id] = pred_total_per_id.get(p.track_id, 0) + 1

        # Greedy bipartite matching on IoU for current frame
        matched_gt_in_frame: Set[int] = set()
        matched_pred_in_frame: Set[int] = set()

        # Sort candidate pairs by IoU
        candidates = []
        for p_idx, p in enumerate(preds):
            for g_idx, g in enumerate(gts):
                iou = compute_iou(p.box, g.box)
                if iou >= iou_thresh:
                    candidates.append((iou, p_idx, g_idx))
        candidates.sort(key=lambda c: c[0], reverse=True)

        for iou, p_idx, g_idx in candidates:
            if p_idx in matched_pred_in_frame or g_idx in matched_gt_in_frame:
                continue
            matched_pred_in_frame.add(p_idx)
            matched_gt_in_frame.add(g_idx)

            p = preds[p_idx]
            g = gts[g_idx]
            gid = g.track_id
            pid = p.track_id
            assert gid is not None

            iou_sum += iou
            matched_boxes_count += 1
            matched_preds_all_time.add(pid)
            gt_frames_tracked_count[gid] = gt_frames_tracked_count.get(gid, 0) + 1
            gt_match_counts[(gid, pid)] = gt_match_counts.get((gid, pid), 0) + 1

            # Check for ID switch or fragmentation
            if gid in last_gt_to_pred:
                prev_pid = last_gt_to_pred[gid]
                prev_frame = last_gt_seen_frame.get(gid, frame_idx - 1)
                if prev_pid != pid:
                    total_idsw += 1
                elif frame_idx > prev_frame + 1:
                    total_frag += 1

            last_gt_to_pred[gid] = pid
            last_gt_seen_frame[gid] = frame_idx

        # False positives and False negatives for this frame
        frame_fp = len(preds) - len(matched_pred_in_frame)
        frame_fn = len(gts) - len(matched_gt_in_frame)
        total_fp += frame_fp
        total_fn += frame_fn

    # Compute MOTA
    if total_gt_boxes > 0:
        mota = 1.0 - ((total_fn + total_fp + total_idsw) / total_gt_boxes)
        motp = (iou_sum / matched_boxes_count) if matched_boxes_count > 0 else 0.0
    else:
        mota = 0.0
        motp = 0.0

    # Compute MT, PT, ML
    mostly_tracked = 0
    partially_tracked = 0
    mostly_lost = 0
    for gid, frames in gt_trajectories.items():
        total_f = len(frames)
        tracked_f = gt_frames_tracked_count.get(gid, 0)
        ratio = tracked_f / total_f if total_f > 0 else 0.0
        if ratio >= 0.80:
            mostly_tracked += 1
        elif ratio <= 0.20:
            mostly_lost += 1
        else:
            partially_tracked += 1

    # Compute IDF1
    # Bipartite matching between GT trajectories and Pred trajectories
    idtp = 0
    used_preds: Set[int] = set()
    # Sort pairs by match count
    pair_matches = sorted(gt_match_counts.items(), key=lambda x: x[1], reverse=True)
    matched_gids: Set[int] = set()
    for (gid, pid), count in pair_matches:
        if gid not in matched_gids and pid not in used_preds:
            idtp += count
            matched_gids.add(gid)
            used_preds.add(pid)

    total_pred_boxes = sum(pred_total_per_id.values())
    idfp = total_pred_boxes - idtp
    idfn = total_gt_boxes - idtp

    denom = (2 * idtp) + idfp + idfn
    idf1 = (2 * idtp) / denom if denom > 0 else 0.0
    idp = idtp / (idtp + idfp) if (idtp + idfp) > 0 else 0.0
    idr = idtp / (idtp + idfn) if (idtp + idfn) > 0 else 0.0

    # Operational metrics: False tracks and continuity
    total_preds_count = len(pred_trajectories)
    pure_false_tracks = sum(1 for pid in pred_trajectories if pid not in matched_preds_all_time)
    false_tracks_per_1000 = (pure_false_tracks / num_frames) * 1000.0

    durations = []
    for gid, frames in gt_trajectories.items():
        total_f = len(frames)
        tracked_f = gt_frames_tracked_count.get(gid, 0)
        durations.append(tracked_f / total_f if total_f > 0 else 0.0)
    mean_continuity = sum(durations) / len(durations) if durations else 0.0

    # HOTA approximation at alpha=0.50
    # DetA = TP / (TP + FP + FN)
    tp_boxes = matched_boxes_count
    deta = tp_boxes / (tp_boxes + total_fp + total_fn) if (tp_boxes + total_fp + total_fn) > 0 else 0.0
    # AssA = IDTP / (IDTP + IDFP + IDFN) approximated from association matches
    assa = idtp / (idtp + idfp + idfn) if (idtp + idfp + idfn) > 0 else 0.0
    hota = math.sqrt(deta * assa) if (deta * assa) > 0 else 0.0

    return TrackingMetrics(
        sequence_name=sequence_name,
        num_frames=num_frames,
        num_gt_trajectories=len(gt_trajectories),
        num_gt_boxes=total_gt_boxes,
        mota=mota,
        motp=motp,
        idf1=idf1,
        idp=idp,
        idr=idr,
        idsw=total_idsw,
        frag=total_frag,
        mostly_tracked=mostly_tracked,
        partially_tracked=partially_tracked,
        mostly_lost=mostly_lost,
        false_tracks_per_1000_frames=false_tracks_per_1000,
        mean_track_continuity=mean_continuity,
        hota=hota,
        deta=deta,
        assa=assa,
    )
