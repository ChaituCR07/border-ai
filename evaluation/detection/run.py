"""CLI runner for object detection evaluation."""
import argparse
import json
import os
import sys
from typing import List

from evaluation.common.manifest import RunManifest
from evaluation.common.tables import markdown_table
from evaluation.datasets.base import DetSample
from evaluation.datasets.cctv_custom import CctvCustomDetectionDataset
from evaluation.detection.metrics import ClassMetrics, evaluate_detection_class
from evaluation.detection.predict import EvaluationDetector


def parse_args(args: List[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run detection evaluation benchmark")
    parser.add_argument("--dataset", choices=["cctv", "coco", "bdd"], default="cctv")
    parser.add_argument("--annotations", type=str, default=None)
    parser.add_argument("--images-dir", type=str, default=None)
    parser.add_argument("--model", type=str, default="yolov8n.pt")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--output-dir", type=str, default="evaluation/runs/detection_latest")
    return parser.parse_args(args)


def run_detection_eval(args: argparse.Namespace) -> None:
    # Resolve dataset paths
    if args.annotations is None:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "cctv_mini")
        args.annotations = os.path.join(base_dir, "annotations.json")
        args.images_dir = base_dir

    dataset = CctvCustomDetectionDataset(annotations_path=args.annotations, images_dir=args.images_dir)
    print(f"Loaded {len(dataset)} samples from {args.annotations}")

    detector = EvaluationDetector(model_name=args.model, conf=args.conf)
    all_preds = [detector.predict_sample(s) for s in dataset]
    all_gts = [s.gt for s in dataset]

    # Evaluate target project classes
    classes_to_eval = ["person", "car", "truck"]
    headers = ["Class", "TP", "FP", "FN", "Precision", "Recall", "F1", "AP@50", "mAP@50:95", "Foot Err (px)"]
    rows = []
    results_dict = {}

    for cls_name in classes_to_eval:
        m: ClassMetrics = evaluate_detection_class(all_preds, all_gts, cls_name=cls_name, score_thresh=args.conf)
        results_dict[cls_name] = {
            "tp": m.tp,
            "fp": m.fp,
            "fn": m.fn,
            "precision": m.precision,
            "recall": m.recall,
            "f1": m.f1,
            "ap50": m.ap50,
            "map_50_95": m.map_50_95,
            "footpoint_err_px": m.mean_footpoint_error_px,
        }
        rows.append([
            cls_name,
            str(m.tp),
            str(m.fp),
            str(m.fn),
            f"{m.precision:.3f}",
            f"{m.recall:.3f}",
            f"{m.f1:.3f}",
            f"{m.ap50:.3f}",
            f"{m.map_50_95:.3f}",
            f"{m.mean_footpoint_error_px:.1f}",
        ])

    print("\n" + markdown_table(headers, rows))

    # Save run manifest
    manifest = RunManifest(
        run_id=os.path.basename(args.output_dir),
        task="detection",
        dataset={"name": args.dataset, "annotations": args.annotations},
        model={"name": args.model},
        inference={"conf": args.conf, "iou": 0.5},
        deployed_thresholds={"person": 0.35, "car": 0.30, "truck": 0.35},
        hardware={"platform": sys.platform},
    )
    manifest.write_json(args.output_dir)
    # Also write metrics summary
    metrics_path = os.path.join(args.output_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(results_dict, f, indent=2)
    print(f"\nRun manifest saved to {os.path.join(args.output_dir, 'manifest.json')}")


if __name__ == "__main__":
    run_detection_eval(parse_args(sys.argv[1:]))
