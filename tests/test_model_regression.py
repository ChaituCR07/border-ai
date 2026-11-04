"""Model regression tests comparing current detection and tracking metrics against stored baselines."""
import json
import os

from evaluation.datasets.base import TrackingFrame, TrackingSequence
from evaluation.datasets.cctv_custom import CctvCustomDetectionDataset
from evaluation.detection.metrics import evaluate_detection_class
from evaluation.detection.predict import EvaluationDetector
from evaluation.tracking.metrics import evaluate_tracking_sequence
from evaluation.tracking.mot_io import MotRow
from evaluation.tracking.run_tracker import run_tracker_on_sequence


class _MiniSequence(TrackingSequence):
    def __init__(self, samples):
        self.samples = samples
        self.name = "cctv_mini_seq"
        self.fps = 10.0
        self.width = 1920
        self.height = 1080
        self.is_static_camera = True

    def frames(self):
        for idx, s in enumerate(self.samples):
            yield TrackingFrame(
                frame_index=idx + 1,
                timestamp=idx / self.fps,
                image_path=s.path,
                gt=s.gt,
            )

    def __len__(self):
        return len(self.samples)


def test_detection_regression_against_baseline() -> None:
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "evaluation", "fixtures", "cctv_mini")
    ann_path = os.path.join(fixture_dir, "annotations.json")
    baseline_path = os.path.join(fixture_dir, "baseline.json")

    assert os.path.exists(ann_path), f"Missing {ann_path}"
    assert os.path.exists(baseline_path), f"Missing {baseline_path}"

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    dataset = CctvCustomDetectionDataset(annotations_path=ann_path, images_dir=fixture_dir)
    assert len(dataset) > 0

    detector = EvaluationDetector()
    predictions = [detector.predict_sample(s) for s in dataset]
    gts = [s.gt for s in dataset]

    # Verify person class
    person_metrics = evaluate_detection_class(predictions, gts, cls_name="person", score_thresh=0.35)
    person_base = baseline["detection_baselines"]["person"]

    # Allow a small 5% tolerance margin
    assert person_metrics.precision >= person_base["precision"] * 0.95, (
        f"Person precision regressed: {person_metrics.precision:.3f} < {person_base['precision'] * 0.95:.3f}"
    )
    assert person_metrics.recall >= person_base["recall"] * 0.95, (
        f"Person recall regressed: {person_metrics.recall:.3f} < {person_base['recall'] * 0.95:.3f}"
    )

    # Verify car class
    car_metrics = evaluate_detection_class(predictions, gts, cls_name="car", score_thresh=0.30)
    car_base = baseline["detection_baselines"]["car"]
    assert car_metrics.precision >= car_base["precision"] * 0.95
    assert car_metrics.recall >= car_base["recall"] * 0.95


def test_tracking_regression_against_baseline() -> None:
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "evaluation", "fixtures", "cctv_mini")
    ann_path = os.path.join(fixture_dir, "annotations.json")
    baseline_path = os.path.join(fixture_dir, "baseline.json")

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    dataset = CctvCustomDetectionDataset(annotations_path=ann_path, images_dir=fixture_dir)
    seq = _MiniSequence(dataset.samples)

    pred_frames = run_tracker_on_sequence(sequence=seq, track_buffer=30, match_thresh=0.7)
    gt_frames = {idx + 1: s.gt for idx, s in enumerate(dataset.samples)}

    tracking_metrics = evaluate_tracking_sequence(gt_frames, pred_frames, sequence_name=seq.name)
    track_base = baseline["tracking_baselines"]

    assert tracking_metrics.mota >= track_base["mota"] * 0.95, (
        f"Tracking MOTA regressed: {tracking_metrics.mota:.3f} < {track_base['mota'] * 0.95:.3f}"
    )
    assert tracking_metrics.idf1 >= track_base["idf1"] * 0.95, (
        f"Tracking IDF1 regressed: {tracking_metrics.idf1:.3f} < {track_base['idf1'] * 0.95:.3f}"
    )
    assert tracking_metrics.idsw <= track_base["max_idsw"], (
        f"Tracking ID switches exceeded threshold: {tracking_metrics.idsw} > {track_base['max_idsw']}"
    )
