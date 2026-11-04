"""Downstream rule-engine alert impact analysis for tracking artifacts.

Translates ID switches, fragmentations, and false tracks into operational
security alert metrics: event recall, event precision, double-counting, and dwell error.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from evaluation.datasets.base import Box, GtObject
from evaluation.detection.metrics import compute_iou
from evaluation.tracking.mot_io import MotRow


@dataclass
class SecurityEvent:
    event_type: str  # "line_crossing" or "loitering"
    track_id: int
    frame_index: int
    timestamp: float
    details: str = ""


@dataclass
class EventImpactReport:
    gt_events_count: int
    pred_events_count: int
    matched_events_count: int
    event_recall: float
    event_precision: float
    double_counted_alerts: int
    mean_dwell_timing_error_s: float
    spurious_phantom_alerts: int


class PerimeterEventSimulator:
    """Simulates operational security rules (Line Crossing & Loitering)."""

    def __init__(
        self,
        fence_line_y: float = 500.0,
        loiter_zone: Tuple[float, float, float, float] = (100.0, 100.0, 400.0, 400.0),
        loiter_threshold_frames: int = 15,
        fps: float = 30.0,
    ) -> None:
        self.fence_line_y = fence_line_y
        self.loiter_zone = loiter_zone  # (x1, y1, x2, y2)
        self.loiter_threshold_frames = loiter_threshold_frames
        self.fps = fps

    def simulate_events(
        self, rows_by_frame: Dict[int, List[MotRow]]
    ) -> List[SecurityEvent]:
        """Detects perimeter events given per-frame tracked bounding boxes."""
        events: List[SecurityEvent] = []

        # State tracking:
        # track_id -> previous foot point y
        last_foot_y: Dict[int, float] = {}
        # track_id -> frames inside loiter zone
        loiter_dwell: Dict[int, int] = {}
        loiter_fired: set = set()
        crossed_fired: set = set()

        all_frames = sorted(rows_by_frame.keys())

        for f_idx in all_frames:
            t = (f_idx - 1) / self.fps
            rows = rows_by_frame[f_idx]

            active_ids_in_frame = set()
            for r in rows:
                tid = r.track_id
                active_ids_in_frame.add(tid)
                fx, fy = r.box.foot_point

                # 1. Line Crossing Check (moving across fence_line_y from top to bottom)
                if tid in last_foot_y:
                    prev_y = last_foot_y[tid]
                    if prev_y < self.fence_line_y <= fy:
                        if tid not in crossed_fired:
                            events.append(
                                SecurityEvent(
                                    event_type="line_crossing",
                                    track_id=tid,
                                    frame_index=f_idx,
                                    timestamp=t,
                                    details=f"Crossed fence at y={self.fence_line_y}",
                                )
                            )
                            crossed_fired.add(tid)

                last_foot_y[tid] = fy

                # 2. Loitering Check
                zx1, zy1, zx2, zy2 = self.loiter_zone
                if zx1 <= fx <= zx2 and zy1 <= fy <= zy2:
                    loiter_dwell[tid] = loiter_dwell.get(tid, 0) + 1
                    if loiter_dwell[tid] >= self.loiter_threshold_frames:
                        if tid not in loiter_fired:
                            events.append(
                                SecurityEvent(
                                    event_type="loitering",
                                    track_id=tid,
                                    frame_index=f_idx,
                                    timestamp=t,
                                    details=f"Loitered for {loiter_dwell[tid]} frames",
                                )
                            )
                            loiter_fired.add(tid)
                else:
                    loiter_dwell[tid] = 0

        return events


def evaluate_tracking_event_impact(
    gt_frames: Dict[int, List[GtObject]],
    pred_frames: Dict[int, List[MotRow]],
    fps: float = 30.0,
    fence_line_y: float = 500.0,
    loiter_threshold_frames: int = 15,
) -> EventImpactReport:
    """Evaluates how tracking flaws directly impact downstream alert generation."""
    simulator = PerimeterEventSimulator(
        fence_line_y=fence_line_y,
        loiter_threshold_frames=loiter_threshold_frames,
        fps=fps,
    )

    # Convert GT frames to MotRow format for simulation
    gt_rows_by_frame: Dict[int, List[MotRow]] = {}
    for f_idx, gts in gt_frames.items():
        gt_rows_by_frame[f_idx] = [
            MotRow(frame=f_idx, track_id=g.track_id or 0, box=g.box)
            for g in gts
            if not g.ignore and g.track_id is not None
        ]

    gt_events = simulator.simulate_events(gt_rows_by_frame)
    pred_events = simulator.simulate_events(pred_frames)

    # Match pred events to GT events based on temporal proximity and overlapping track
    matched_gt_indices: set = set()
    pred_to_gt_map: Dict[int, int] = {}
    dwell_timing_errors: List[float] = []

    for p_idx, pe in enumerate(pred_events):
        best_diff = float("inf")
        best_gt_idx = -1

        for g_idx, ge in enumerate(gt_events):
            if pe.event_type == ge.event_type:
                time_diff = abs(pe.timestamp - ge.timestamp)
                # Allow temporal tolerance of +/- 1.0 second
                if time_diff <= 1.0 and time_diff < best_diff:
                    best_diff = time_diff
                    best_gt_idx = g_idx

        if best_gt_idx >= 0:
            pred_to_gt_map[p_idx] = best_gt_idx
            matched_gt_indices.add(best_gt_idx)
            if pe.event_type == "loitering":
                dwell_timing_errors.append(best_diff)

    matched_count = len(matched_gt_indices)
    recall = matched_count / len(gt_events) if gt_events else 1.0
    prec = len(pred_to_gt_map) / len(pred_events) if pred_events else 1.0

    # Check for double-counting: Multiple pred events mapped to the SAME GT event
    gt_alert_counts: Dict[int, int] = {}
    for g_idx in pred_to_gt_map.values():
        gt_alert_counts[g_idx] = gt_alert_counts.get(g_idx, 0) + 1

    double_counts = sum(count - 1 for count in gt_alert_counts.values() if count > 1)
    spurious = len(pred_events) - len(pred_to_gt_map)
    mean_dwell_err = (
        sum(dwell_timing_errors) / len(dwell_timing_errors)
        if dwell_timing_errors
        else 0.0
    )

    return EventImpactReport(
        gt_events_count=len(gt_events),
        pred_events_count=len(pred_events),
        matched_events_count=matched_count,
        event_recall=recall,
        event_precision=prec,
        double_counted_alerts=double_counts,
        mean_dwell_timing_error_s=mean_dwell_err,
        spurious_phantom_alerts=spurious,
    )
