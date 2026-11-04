"""Unit tests for tracking-to-rule event impact evaluation."""
from evaluation.datasets.base import Box, GtObject
from evaluation.tracking.event_impact import (
    PerimeterEventSimulator,
    evaluate_tracking_event_impact,
)
from evaluation.tracking.mot_io import MotRow


def test_clean_line_crossing_event() -> None:
    # GT moves from y=400 to y=600 across fence at y=500
    gt_frames = {
        1: [GtObject("person", Box(100, 450, 40, 40), track_id=1)],  # foot y = 490
        2: [GtObject("person", Box(100, 470, 40, 40), track_id=1)],  # foot y = 510 (crossed!)
        3: [GtObject("person", Box(100, 490, 40, 40), track_id=1)],
    }
    pred_frames = {
        1: [MotRow(frame=1, track_id=10, box=Box(100, 450, 40, 40))],
        2: [MotRow(frame=2, track_id=10, box=Box(100, 470, 40, 40))],
        3: [MotRow(frame=3, track_id=10, box=Box(100, 490, 40, 40))],
    }

    report = evaluate_tracking_event_impact(
        gt_frames, pred_frames, fence_line_y=500.0, fps=10.0
    )
    assert report.gt_events_count == 1
    assert report.pred_events_count == 1
    assert report.event_recall == 1.0
    assert report.event_precision == 1.0
    assert report.double_counted_alerts == 0
    assert report.spurious_phantom_alerts == 0


def test_id_switch_causes_double_counting_alert() -> None:
    # 1 GT crosses fence at frame 2
    # Pred 1 crosses at frame 2, then ID switches to Pred 2 which also records crossing
    gt_frames = {
        1: [GtObject("person", Box(100, 450, 40, 40), track_id=1)],
        2: [GtObject("person", Box(100, 470, 40, 40), track_id=1)],  # foot y = 510
        3: [GtObject("person", Box(100, 472, 40, 40), track_id=1)],
        4: [GtObject("person", Box(100, 475, 40, 40), track_id=1)],
    }
    pred_frames = {
        1: [MotRow(frame=1, track_id=10, box=Box(100, 450, 40, 40))],
        2: [MotRow(frame=2, track_id=10, box=Box(100, 470, 40, 40))],  # Alert 1
        # ID switch at frame 3: new track starts at y=450, then crosses at frame 4
        3: [MotRow(frame=3, track_id=20, box=Box(100, 450, 40, 40))],
        4: [MotRow(frame=4, track_id=20, box=Box(100, 475, 40, 40))],  # Alert 2
    }

    report = evaluate_tracking_event_impact(
        gt_frames, pred_frames, fence_line_y=500.0, fps=10.0
    )
    assert report.gt_events_count == 1
    assert report.pred_events_count == 2
    assert report.double_counted_alerts == 1


def test_phantom_false_track_triggers_spurious_alert() -> None:
    # GT walks far away from fence
    gt_frames = {
        1: [GtObject("person", Box(10, 10, 20, 20), track_id=1)],
        2: [GtObject("person", Box(10, 15, 20, 20), track_id=1)],
    }
    # Tracker produces a false phantom track crossing the fence
    pred_frames = {
        1: [MotRow(frame=1, track_id=99, box=Box(50, 470, 40, 20))],  # foot y = 490
        2: [MotRow(frame=2, track_id=99, box=Box(50, 490, 40, 20))],  # foot y = 510 (spurious!)
    }

    report = evaluate_tracking_event_impact(
        gt_frames, pred_frames, fence_line_y=500.0, fps=10.0
    )
    assert report.gt_events_count == 0
    assert report.pred_events_count == 1
    assert report.spurious_phantom_alerts == 1
    assert report.event_precision == 0.0
