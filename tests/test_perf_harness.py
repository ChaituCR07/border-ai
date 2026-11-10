"""Unit tests for performance harness components: sampler, stability, manifest, and dry-run execution."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from perf.harness.manifest import BenchmarkSpec, ExecutionManifest
from perf.harness.runner import BenchmarkRunner
from perf.harness.sampler import HardwareTelemetry, ResourceSample, ResourceSampler
from perf.harness.stability import (
    RunBudgets,
    RunTelemetryData,
    evaluate_run_stability,
    slope_per_min,
)
from perf.harness.summarise import SingleRepetitionSummary, aggregate_repetitions


def test_slope_per_min_linear_regression():
    """Verify queue growth slope in frames per minute across flat, rising, and falling series."""
    # Flat series: slope must be exactly 0.0
    assert slope_per_min([0.0, 30.0, 60.0], [5.0, 5.0, 5.0]) == 0.0

    # Steadily rising: +2 frames every 30 seconds = +4 frames / minute
    ts = [0.0, 30.0, 60.0, 90.0]
    depths = [2.0, 4.0, 6.0, 8.0]
    slope = slope_per_min(ts, depths)
    assert abs(slope - 4.0) < 1e-4

    # Steadily falling: -1 frame every 60 seconds = -1 frame / minute
    ts_fall = [0.0, 60.0, 120.0]
    depths_fall = [10.0, 9.0, 8.0]
    slope_fall = slope_per_min(ts_fall, depths_fall)
    assert abs(slope_fall - (-1.0)) < 1e-4


def test_stability_evaluation_all_criteria():
    """Verify stability detector correctly identifies VALID, UNSTABLE, and THROTTLED conditions."""
    budgets = RunBudgets(drop_rate_max=0.01, freshness_p95_ms=500.0, max_queue_slope_per_min=1.0)

    # 1. Perfectly stable run
    clean_run = RunTelemetryData(
        queues={"ingest": ([0.0, 60.0, 120.0], [2.0, 2.0, 2.0], 30)},
        drop_rate=0.001,
        freshness_p95_ms=45.0,
        processing_p95_ms=120.0,
        clock_frequencies=[1200.0, 1200.0, 1200.0],
        process_restarts=0,
        budgets=budgets,
    )
    v1 = evaluate_run_stability(clean_run)
    assert v1.status == "VALID"
    assert v1.is_valid is True
    assert len(v1.reasons) == 0

    # 2. Queue growing beyond capacity threshold -> UNSTABLE
    queue_leak_run = RunTelemetryData(
        queues={"ingest": ([0.0, 30.0, 60.0], [5.0, 12.0, 20.0], 30)},  # final depth 20 > 50% of 30
        drop_rate=0.001,
        freshness_p95_ms=80.0,
        processing_p95_ms=120.0,
        clock_frequencies=[1200.0, 1200.0],
        budgets=budgets,
    )
    v2 = evaluate_run_stability(queue_leak_run)
    assert v2.status == "UNSTABLE"
    assert v2.is_valid is False
    assert any("queue 'ingest' growing" in r for r in v2.reasons)

    # 3. High drop rate -> UNSTABLE
    drop_run = RunTelemetryData(
        queues={"ingest": ([0.0, 60.0], [2.0, 2.0], 30)},
        drop_rate=0.035,  # 3.5% > 1.0%
        freshness_p95_ms=45.0,
        processing_p95_ms=120.0,
        clock_frequencies=[1200.0, 1200.0],
        budgets=budgets,
    )
    v3 = evaluate_run_stability(drop_run)
    assert v3.status == "UNSTABLE"
    assert any("drop rate 3.5%" in r for r in v3.reasons)

    # 4. Thermal throttling (>10% clock frequency degradation) -> THROTTLED
    throttled_run = RunTelemetryData(
        queues={"ingest": ([0.0, 60.0], [2.0, 2.0], 30)},
        drop_rate=0.0,
        freshness_p95_ms=45.0,
        processing_p95_ms=120.0,
        clock_frequencies=[1400.0, 1100.0],  # 21.4% drop
        budgets=budgets,
    )
    v4 = evaluate_run_stability(throttled_run)
    assert v4.status == "THROTTLED"
    assert v4.is_valid is False
    assert any("clock throttling detected" in r for r in v4.reasons)


def test_resource_sample_serialization_and_csv():
    """Verify ResourceSample formats CSV rows with required float formatting and n/a fallbacks."""
    sample = ResourceSample(
        timestamp_s=1700000000.123,
        elapsed_s=15.0,
        cpu_percent=42.3,
        system_cpu_percent=12.1,
        process_rss_mb=450.6,
        system_ram_used_mb=3500.0,
        system_ram_total_mb=8192.0,
        gpu_util_percent=None,
        gpu_mem_used_mb=None,
    )
    row = sample.to_csv_row()
    assert row["timestamp_s"] == "1700000000.123"
    assert row["cpu_percent"] == "42.3"
    assert row["gpu_util_percent"] == "n/a"
    assert row["gpu_mem_used_mb"] == "n/a"


def test_benchmark_spec_validation():
    """Spec validator must reject illegal configurations with clear errors."""
    valid_spec = {
        "id": "spec-valid",
        "stack": {"device": "auto", "model": "yolov8s"},
        "cameras": 4,
        "workload": "typical",
        "measure_s": 45.0,
    }
    s = BenchmarkSpec.from_dict(valid_spec)
    assert s.cameras == 4

    # Invalid cameras count (< 1)
    try:
        BenchmarkSpec.from_dict({**valid_spec, "cameras": 0})
        assert False, "Should fail on cameras=0"
    except ValueError as e:
        assert "cameras must be >= 1" in str(e)

    # Invalid workload name
    try:
        BenchmarkSpec.from_dict({**valid_spec, "workload": "unknown_profile"})
        assert False, "Should fail on unknown workload"
    except ValueError as e:
        assert "must be one of" in str(e)

    # Short measurement interval (< 30s)
    try:
        BenchmarkSpec.from_dict({**valid_spec, "measure_s": 15.0})
        assert False, "Should fail on measure_s < 30"
    except ValueError as e:
        assert "measure_s must be >= 30" in str(e)


def test_repetition_aggregation_min_median_max():
    """aggregate_repetitions must calculate accurate median, min, max, and overall status."""
    r1 = SingleRepetitionSummary(
        repetition_index=0,
        cameras=2,
        duration_s=60.0,
        analytics_fps_per_cam=10.0,
        total_analytics_fps=20.0,
        processing_latency_p50_ms=25.0,
        processing_latency_p95_ms=35.0,
        processing_latency_p99_ms=45.0,
        freshness_p95_ms=30.0,
        drop_rate=0.001,
        cpu_percent=40.0,
        ram_mb=400.0,
        alert_latency_p95_s=0.25,
        verdict="VALID",
        stages_p50_ms={"detect": 14.0},
        stages_p95_ms={"detect": 16.0},
    )

    r2 = SingleRepetitionSummary(
        repetition_index=1,
        cameras=2,
        duration_s=60.0,
        analytics_fps_per_cam=12.0,
        total_analytics_fps=24.0,
        processing_latency_p50_ms=20.0,
        processing_latency_p95_ms=30.0,
        processing_latency_p99_ms=40.0,
        freshness_p95_ms=25.0,
        drop_rate=0.002,
        cpu_percent=45.0,
        ram_mb=420.0,
        alert_latency_p95_s=0.20,
        verdict="VALID",
        stages_p50_ms={"detect": 12.0},
        stages_p95_ms={"detect": 14.0},
    )

    agg = aggregate_repetitions("test-spec", [r1, r2])
    assert agg.spec_id == "test-spec"
    assert agg.cameras == 2
    assert agg.verdict == "VALID"
    assert agg.analytics_fps_median == 11.0
    assert agg.analytics_fps_min == 10.0
    assert agg.analytics_fps_max == 12.0
    assert agg.stages_breakdown_p50["detect"] == 13.0
    assert agg.stages_breakdown_p95["detect"] == 15.0


def test_harness_dry_run_execution():
    """Run full benchmark runner lifecycle and verify outputs are written to disk."""
    with TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "run_test"
        spec = BenchmarkSpec.from_dict({
            "id": "dry-run-spec",
            "stack": {"model": "yolov8s", "analytics_fps": 10},
            "cameras": 1,
            "workload": "light",
            "measure_s": 30.0,
            "repeat": 1,
        })

        runner = BenchmarkRunner(spec, output_dir=out_path)
        summary = runner.run()

        assert summary.cameras == 1
        assert summary.verdict == "VALID"
        assert (out_path / "manifest.json").exists()
        assert (out_path / "summary.json").exists()
        assert (out_path / "rep_1" / "resources.csv").exists()
        assert (out_path / "rep_1" / "frame_trace.jsonl").exists()
