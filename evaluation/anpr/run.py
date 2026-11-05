#!/usr/bin/env python3
"""CLI benchmark runner for ANPR evaluation (Modes M1, M2, M3).

Usage:
  python3 -m evaluation.anpr.run [--fixtures-dir DIR] [--output-dir DIR] [--mode {M1,M2,M3,all}]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from evaluation.anpr.calibration import ece, wilson_score_interval
from evaluation.anpr.confusion_analysis import analyze_character_confusion
from evaluation.anpr.consensus import (
    EarlyStopConfig,
    TrackFrameRead,
    VehicleTrack,
    benchmark_strategies,
    evaluate_accuracy_vs_frames,
)
from evaluation.anpr.datasets.india_anpr import IndiaAnprDataset
from evaluation.anpr.funnel import VehicleFunnelInput, build_pipeline_funnel
from evaluation.anpr.metrics import corpus_metrics, plate_key, score_pair
from evaluation.anpr.predict import OcrPipelineConfig, PipelineEvaluator
from evaluation.anpr.slices import analyze_slices
from evaluation.anpr.watchlist_eval import simulate_watchlist_collisions


def run_benchmark(fixtures_dir: Path, output_dir: Path, mode: str = "all") -> int:
    labels_file = fixtures_dir / "labels.json"
    if not labels_file.exists():
        print(f"[!] Error: fixture file not found at {labels_file}", file=sys.stderr)
        return 1

    run_id = f"run-{time.strftime('%Y%m%d')}-anpr-cli"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Starting BorderVision ANPR Evaluation Benchmark [Run ID: {run_id}]")
    print(f"    Mode: {mode} | Fixtures: {fixtures_dir}")

    dataset = IndiaAnprDataset(labels_file, fixtures_dir)
    samples = list(dataset)
    print(f"[*] Loaded {len(samples)} samples across {len(dataset.vehicles)} distinct vehicles.")

    manifest = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_samples": len(samples),
        "total_vehicles": len(dataset.vehicles),
        "results": {},
    }

    # Mode M1: Oracle Crops
    if mode in ("M1", "all"):
        print("\n--- Running Mode M1 (Oracle Crops) ---")
        evaluator_m1 = PipelineEvaluator(OcrPipelineConfig(mode="M1", position_aware_correction=True))
        results_m1 = evaluator_m1.evaluate_batch(samples)
        pairs_m1 = [score_pair(s.plate_norm, r.pred_text, plate_key) for s, r in zip(samples, results_m1)]
        metrics_m1 = corpus_metrics(pairs_m1)
        confs_m1 = [r.confidence for r in results_m1]
        correct_m1 = [p["exact"] for p in pairs_m1]
        ece_m1 = ece(confs_m1, correct_m1)

        manifest["results"]["M1"] = {
            **metrics_m1,
            "ece": round(ece_m1, 4),
            "ci_exact": wilson_score_interval(sum(correct_m1), len(correct_m1)),
        }
        print(f"    Exact Accuracy: {metrics_m1['plate_exact']:.1%}")
        print(f"    Character Acc : {metrics_m1['char_accuracy']:.1%}")
        print(f"    Read Rate     : {metrics_m1['read_rate']:.1%}")
        print(f"    ECE           : {ece_m1:.4f}")

    # Mode M2: Single-Frame Cascaded Pipeline
    if mode in ("M2", "all"):
        print("\n--- Running Mode M2 (Single-Frame Cascaded Pipeline) ---")
        evaluator_m2 = PipelineEvaluator(OcrPipelineConfig(mode="M2", position_aware_correction=True))
        results_m2 = evaluator_m2.evaluate_batch(samples)
        pairs_m2 = [score_pair(s.plate_norm, r.pred_text, plate_key) for s, r in zip(samples, results_m2)]
        metrics_m2 = corpus_metrics(pairs_m2)
        manifest["results"]["M2"] = {
            **metrics_m2,
            "ci_exact": wilson_score_interval(sum(p["exact"] for p in pairs_m2), len(pairs_m2)),
        }
        print(f"    Exact Accuracy: {metrics_m2['plate_exact']:.1%}")
        print(f"    Look-Alike Acc: {metrics_m2['lookalike_equiv']:.1%}")
        print(f"    Read Rate     : {metrics_m2['read_rate']:.1%}")

        # Slices analysis
        slice_report = analyze_slices(samples, results_m2)
        min_height = slice_report.minimum_height_for_target_accuracy(0.88)
        print(f"    Min Plate Height for >=88% Exact Acc: {min_height}")

    # Mode M3: Multi-Frame Consensus
    if mode in ("M3", "all"):
        print("\n--- Running Mode M3 (Multi-Frame Positional Consensus) ---")
        # Build synthetic tracks
        tracks = []
        for v_id in dataset.vehicles:
            v_samples = [s for s in samples if s.vehicle_id == v_id]
            reads = [
                TrackFrameRead(
                    frame_index=idx,
                    text=s.plate_norm,
                    confidence=0.92,
                    timestamp_ms=idx * 40.0,
                )
                for idx, s in enumerate(v_samples)
            ]
            if reads:
                tracks.append(
                    VehicleTrack(
                        vehicle_id=v_id,
                        gt_plate=v_samples[0].plate_norm,
                        reads=reads,
                    )
                )

        early_cfg = EarlyStopConfig(min_reads=3, confidence_thresh=0.85)
        bench = benchmark_strategies(tracks, early_stop=early_cfg)
        manifest["results"]["M3"] = [
            {
                "strategy": b.strategy,
                "exact_acc": round(b.exact_accuracy, 4),
                "calls_saved": round(b.pct_calls_saved, 4),
                "avg_frames": round(b.avg_frames_used, 1),
            }
            for b in bench
        ]
        s5 = next(b for b in bench if b.strategy == "S5")
        print(f"    S5 Positional Exact Acc: {s5.exact_accuracy:.1%}")
        print(f"    S5 Compute Calls Saved : {s5.pct_calls_saved:.1%}")

    # Save manifest
    out_file = output_dir / f"anpr_{run_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n[OK] Evaluation complete. Saved run manifest to {out_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ANPR Evaluation Benchmark")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("evaluation/fixtures/anpr_synth"),
        help="Path to ANPR fixtures folder containing labels.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/runs"),
        help="Directory to save output run manifests",
    )
    parser.add_argument(
        "--mode",
        choices=["M1", "M2", "M3", "all"],
        default="all",
        help="Evaluation mode to run",
    )
    args = parser.parse_args()
    return run_benchmark(args.fixtures_dir, args.output_dir, args.mode)


if __name__ == "__main__":
    sys.exit(main())
