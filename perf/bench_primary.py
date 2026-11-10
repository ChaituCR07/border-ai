#!/usr/bin/env python3
"""Primary multi-camera scaling benchmark runner (1 / 2 / 4 / 8 cameras).

Usage:
  python3 -m perf.bench_primary [--fast] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List

from perf.harness.manifest import BenchmarkSpec
from perf.harness.report import (
    format_readme_metrics_block,
    format_scaling_table,
    format_stage_breakdown_table,
)
from perf.harness.runner import BenchmarkRunner
from perf.harness.summarise import AggregatedBenchmarkSummary


def load_spec_file(path: Path, fast: bool = False) -> BenchmarkSpec:
    """Load benchmark spec from YAML/JSON and apply fast-mode overrides if requested."""
    text = path.read_text(encoding="utf-8")
    data: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if v.isdigit():
                data[k] = int(v)
            elif v.replace(".", "", 1).isdigit():
                data[k] = float(v)
            elif v.lower() in ("true", "false"):
                data[k] = v.lower() == "true"
            elif v:
                data[k] = v

    # Fallback to defaults
    spec_dict = {
        "id": data.get("id", path.stem),
        "stack": {
            "mode": "rtsp_live",
            "model": "yolov8s",
            "imgsz": 640,
            "device": "auto",
            "analytics_fps": data.get("analytics_fps", 10),
            "anpr": True,
            "live_view": True,
        },
        "cameras": data.get("cameras", 1),
        "workload": data.get("workload", "typical"),
        "warmup_s": 5.0 if fast else float(data.get("warmup_s", 60.0)),
        "measure_s": 30.0 if fast else float(data.get("measure_s", 300.0)),
        "cooldown_s": 2.0 if fast else float(data.get("cooldown_s", 30.0)),
        "repeat": 1 if fast else int(data.get("repeat", 3)),
    }
    return BenchmarkSpec.from_dict(spec_dict)


def run_primary_benchmarks(fast: bool = False, output_base: Path = Path("perf/runs")) -> int:
    camera_counts = [1, 2, 4, 8]
    specs_dir = Path("perf/specs")
    summaries: List[AggregatedBenchmarkSummary] = []
    run_id = f"run-{time.strftime('%Y%m%d')}-primary-scaling"

    print("=" * 80)
    print(f" BorderVision Primary Scaling Benchmark [Run ID: {run_id}]")
    print(f" Cameras: {camera_counts} | Mode: {'Fast (Iteration)' if fast else 'Report (3 reps, 300s window)'}")
    print("=" * 80)

    for n in camera_counts:
        spec_path = specs_dir / f"primary_n{n}.yaml"
        if not spec_path.exists():
            print(f"[!] Warning: {spec_path} missing; creating dynamically", file=sys.stderr)
            spec_data = {
                "id": f"perf-primary-n{n}",
                "stack": {"device": "auto", "model": "yolov8s", "analytics_fps": 10},
                "cameras": n,
                "workload": "typical",
                "measure_s": 30.0 if fast else 300.0,
                "repeat": 1 if fast else 3,
            }
            spec = BenchmarkSpec.from_dict(spec_data)
        else:
            spec = load_spec_file(spec_path, fast=fast)

        out_dir = output_base / f"{spec.id}_{run_id}"
        runner = BenchmarkRunner(spec, output_dir=out_dir)
        print(f"\n[*] Executing benchmark for N = {n} camera(s) (reps = {spec.repeat})...")
        t0 = time.time()
        summary = runner.run()
        elapsed = time.time() - t0

        summaries.append(summary)
        print(
            f"    -> Done in {elapsed:.1f}s | Verdict: {summary.verdict} | "
            f"FPS/cam: {summary.analytics_fps_median:.1f} | Latency p95: {summary.proc_lat_p95_median:.1f}ms | "
            f"Drop: {summary.drop_rate_median:.2%}"
        )

    # Save consolidated summary
    consolidated_path = output_base / f"primary_scaling_summary_{run_id}.json"
    consolidated_data = {
        "run_id": run_id,
        "date": time.strftime("%Y-%m-%d"),
        "hardware": "Apple M1 (8 cores, 8GB Unified Memory, macOS 26.6.2)",
        "summaries": [s.to_dict() for s in summaries],
    }
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_data, f, indent=2)

    print("\n" + "=" * 80)
    print(" Consolidated Multi-Camera Scaling Results (ADR 0041)")
    print("=" * 80)
    scaling_table = format_scaling_table(summaries)
    print(scaling_table)

    print("\n" + "=" * 80)
    print(" Per-Stage Latency Breakdown (ms p50 / p95)")
    print("=" * 80)
    stage_table = format_stage_breakdown_table(summaries)
    print(stage_table)

    print("\n" + "=" * 80)
    print(" README Metrics Block")
    print("=" * 80)
    readme_metrics = format_readme_metrics_block(summaries[2], run_id)  # N=4 primary deployed
    print(readme_metrics)

    print(f"\n[OK] Benchmark run saved to {consolidated_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Primary Scaling Benchmark (1/2/4/8 Cameras)")
    parser.add_argument("--fast", action="store_true", help="Run shortened iteration mode (30s window, 1 rep)")
    parser.add_argument("--output-dir", type=Path, default=Path("perf/runs"), help="Output directory")
    args = parser.parse_args()
    return run_primary_benchmarks(fast=args.fast, output_base=args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
