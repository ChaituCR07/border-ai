"""CLI runner for multi-object tracking evaluation."""
import argparse
import json
import os
import sys
from typing import List

from evaluation.common.manifest import RunManifest
from evaluation.common.tables import markdown_table
from evaluation.datasets.base import TrackingFrame, TrackingSequence
from evaluation.datasets.cctv_custom import CctvCustomDetectionDataset
from evaluation.tracking.metrics import TrackingMetrics, evaluate_tracking_sequence
from evaluation.tracking.mot_io import MotRow
from evaluation.tracking.run_tracker import run_tracker_on_sequence


class _SeqWrapper(TrackingSequence):
    def __init__(self, samples):
        self.samples = samples
        self.name = "cctv_eval_seq"
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


def parse_args(args: List[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run tracking evaluation benchmark")
    parser.add_argument("--dataset", choices=["cctv", "mot17"], default="cctv")
    parser.add_argument("--annotations", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default="evaluation/runs/tracking_latest")
    parser.add_argument("--track-buffer", type=int, default=30)
    parser.add_argument("--match-thresh", type=float, default=0.7)
    return parser.parse_args(args)


def run_tracking_eval(args: argparse.Namespace) -> None:
    if args.annotations is None:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "cctv_mini")
        args.annotations = os.path.join(base_dir, "annotations.json")
        images_dir = base_dir
    else:
        images_dir = os.path.dirname(args.annotations)

    dataset = CctvCustomDetectionDataset(annotations_path=args.annotations, images_dir=images_dir)
    seq = _SeqWrapper(dataset.samples)

    pred_frames = run_tracker_on_sequence(
        sequence=seq,
        track_buffer=args.track_buffer,
        match_thresh=args.match_thresh,
    )
    gt_frames = {idx + 1: s.gt for idx, s in enumerate(dataset.samples)}

    metrics = evaluate_tracking_sequence(gt_frames, pred_frames, sequence_name=seq.name)

    headers = ["Metric", "Value"]
    rows = [
        ["Sequence", metrics.sequence_name],
        ["Frames Evaluated", str(metrics.num_frames)],
        ["GT Trajectories", str(metrics.num_gt_trajectories)],
        ["GT Boxes", str(metrics.num_gt_boxes)],
        ["HOTA", f"{metrics.hota:.3f}"],
        ["MOTA", f"{metrics.mota:.3f}"],
        ["IDF1", f"{metrics.idf1:.3f}"],
        ["ID Switches", str(metrics.idsw)],
        ["Fragmentations", str(metrics.frag)],
        ["Mostly Tracked (MT)", str(metrics.mostly_tracked)],
        ["Mostly Lost (ML)", str(metrics.mostly_lost)],
        ["False Tracks / 1000f", f"{metrics.false_tracks_per_1000_frames:.1f}"],
        ["Mean Track Continuity", f"{metrics.mean_track_continuity:.2f}"],
    ]

    print("\n" + markdown_table(headers, rows))

    manifest = RunManifest(
        run_id=os.path.basename(args.output_dir),
        task="tracking",
        dataset={"name": args.dataset, "annotations": args.annotations},
        model={"name": "bytetrack"},
        inference={"track_buffer": args.track_buffer, "match_thresh": args.match_thresh},
        deployed_thresholds={"person": 0.35},
        hardware={"platform": sys.platform},
    )
    manifest.write_json(args.output_dir)
    metrics_path = os.path.join(args.output_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "hota": metrics.hota,
                "mota": metrics.mota,
                "idf1": metrics.idf1,
                "idsw": metrics.idsw,
                "continuity": metrics.mean_track_continuity,
            },
            f,
            indent=2,
        )
    print(f"\nRun manifest saved to {os.path.join(args.output_dir, 'manifest.json')}")


if __name__ == "__main__":
    run_tracking_eval(parse_args(sys.argv[1:]))
