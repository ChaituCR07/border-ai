"""Known-answer tests for tracking metrics and MOT format I/O."""
import os
import tempfile

from evaluation.datasets.base import Box, GtObject
from evaluation.tracking.metrics import evaluate_tracking_sequence
from evaluation.tracking.mot_io import MotRow, read_mot_file, write_mot_file


def test_mot_io_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test_mot.txt")
        rows_by_frame = {
            1: [
                MotRow(frame=1, track_id=1, box=Box(10.0, 20.0, 30.0, 40.0), conf=0.95),
                MotRow(frame=1, track_id=2, box=Box(100.0, 200.0, 50.0, 80.0), conf=0.88),
            ],
            2: [
                MotRow(frame=2, track_id=1, box=Box(12.0, 22.0, 30.0, 40.0), conf=0.92),
            ],
        }

        write_mot_file(csv_path, rows_by_frame)
        loaded = read_mot_file(csv_path)

        assert 1 in loaded
        assert 2 in loaded
        assert len(loaded[1]) == 2
        assert len(loaded[2]) == 1

        r1 = loaded[1][0]
        assert r1.frame == 1
        assert r1.track_id == 1
        assert r1.box.x == 10.0
        assert r1.box.y == 20.0
        assert r1.box.w == 30.0
        assert r1.box.h == 40.0
        assert abs(r1.conf - 0.95) < 1e-4


def test_tracking_metrics_perfect_sequence() -> None:
    # 2 trajectories over 5 frames
    gt_frames = {}
    pred_frames = {}

    for f in range(1, 6):
        gt_frames[f] = [
            GtObject("person", Box(f * 10.0, 50.0, 40.0, 80.0), track_id=1),
            GtObject("person", Box(100.0 + f * 5.0, 200.0, 40.0, 80.0), track_id=2),
        ]
        pred_frames[f] = [
            MotRow(frame=f, track_id=10, box=Box(f * 10.0, 50.0, 40.0, 80.0)),
            MotRow(frame=f, track_id=20, box=Box(100.0 + f * 5.0, 200.0, 40.0, 80.0)),
        ]

    m = evaluate_tracking_sequence(gt_frames, pred_frames, sequence_name="perfect_seq")
    assert m.num_frames == 5
    assert m.num_gt_trajectories == 2
    assert m.num_gt_boxes == 10
    assert m.mota == 1.0
    assert m.motp == 1.0
    assert m.idf1 == 1.0
    assert m.idsw == 0
    assert m.frag == 0
    assert m.mostly_tracked == 2
    assert m.mostly_lost == 0
    assert m.false_tracks_per_1000_frames == 0.0
    assert m.mean_track_continuity == 1.0
    assert m.hota == 1.0


def test_tracking_metrics_single_id_switch() -> None:
    # 1 GT over 4 frames: frames 1-2 tracked by pred 10; frames 3-4 tracked by pred 20
    gt_frames = {}
    pred_frames = {}

    for f in range(1, 5):
        gt_frames[f] = [GtObject("person", Box(100.0, 100.0, 50.0, 50.0), track_id=1)]

    pred_frames[1] = [MotRow(frame=1, track_id=10, box=Box(100.0, 100.0, 50.0, 50.0))]
    pred_frames[2] = [MotRow(frame=2, track_id=10, box=Box(100.0, 100.0, 50.0, 50.0))]
    pred_frames[3] = [MotRow(frame=3, track_id=20, box=Box(100.0, 100.0, 50.0, 50.0))]
    pred_frames[4] = [MotRow(frame=4, track_id=20, box=Box(100.0, 100.0, 50.0, 50.0))]

    m = evaluate_tracking_sequence(gt_frames, pred_frames, sequence_name="idsw_seq")
    assert m.idsw == 1
    # MOTA = 1 - (FN + FP + IDSW)/GT = 1 - (0 + 0 + 1)/4 = 0.75
    assert m.mota == 0.75
    assert m.mostly_tracked == 1


def test_tracking_metrics_fragmentation() -> None:
    # 1 GT over 3 frames, frame 2 is missed by detector
    gt_frames = {
        1: [GtObject("person", Box(50.0, 50.0, 40.0, 40.0), track_id=1)],
        2: [GtObject("person", Box(50.0, 50.0, 40.0, 40.0), track_id=1)],
        3: [GtObject("person", Box(50.0, 50.0, 40.0, 40.0), track_id=1)],
    }
    pred_frames = {
        1: [MotRow(frame=1, track_id=9, box=Box(50.0, 50.0, 40.0, 40.0))],
        # Frame 2 is missing
        3: [MotRow(frame=3, track_id=9, box=Box(50.0, 50.0, 40.0, 40.0))],
    }

    m = evaluate_tracking_sequence(gt_frames, pred_frames, sequence_name="frag_seq")
    assert m.frag == 1
    assert m.idsw == 0


def test_tracking_metrics_pure_false_track() -> None:
    # 1 GT trajectory + 1 pure phantom false track across 10 frames
    gt_frames = {f: [GtObject("person", Box(0, 0, 50, 50), track_id=1)] for f in range(1, 11)}
    pred_frames = {
        f: [
            MotRow(frame=f, track_id=1, box=Box(0, 0, 50, 50)),
            MotRow(frame=f, track_id=999, box=Box(800, 800, 50, 50)),  # Pure false track
        ]
        for f in range(1, 11)
    }

    m = evaluate_tracking_sequence(gt_frames, pred_frames, sequence_name="false_track_seq")
    # 1 false track in 10 frames -> (1 / 10) * 1000 = 100.0 false tracks per 1000 frames
    assert m.false_tracks_per_1000_frames == 100.0
