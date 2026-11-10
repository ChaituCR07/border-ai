"""Unit tests for in-engine stage metrics, HDR histograms, and trace sampling."""

import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from engine.observability.metrics import Metrics, PurePythonHdrHistogram, StageStats
from engine.observability.trace import FrameTrace, TraceSampler


def test_hdr_histogram_crafted_percentiles():
    """Verify p50, p90, p95, p99 percentiles on known uniform distribution 1..100 ms."""
    stats = StageStats()
    for ms in range(1, 101):
        stats.record_ms(float(ms))

    assert stats.count == 100
    snap = stats.snapshot()

    # In uniform 1..100: p50 should be ~50.5, p95 ~95.0, p99 ~99.0
    assert 48.0 <= snap["p50_ms"] <= 53.0
    assert 93.0 <= snap["p95_ms"] <= 97.0
    assert 97.0 <= snap["p99_ms"] <= 100.0
    assert snap["max_ms"] == 100.0


def test_hdr_histogram_merge_equivalence():
    """Merging two histograms must equal the union of their samples."""
    h1 = StageStats()
    h2 = StageStats()
    h_combined = StageStats()

    for val in range(1, 51):
        h1.record_ms(float(val))
        h_combined.record_ms(float(val))

    for val in range(51, 101):
        h2.record_ms(float(val))
        h_combined.record_ms(float(val))

    h1.merge(h2)
    assert h1.count == 100
    assert abs(h1.get_percentile_ms(50.0) - h_combined.get_percentile_ms(50.0)) < 1.0
    assert abs(h1.get_percentile_ms(95.0) - h_combined.get_percentile_ms(95.0)) < 1.0


def test_metrics_stage_context_manager():
    """Verify Metrics.stage accurately measures elapsed time and handles exceptions."""
    sync_called = []

    def mock_sync():
        sync_called.append(True)

    metrics = Metrics(sync=mock_sync)

    # Normal execution
    with metrics.stage("detect", "CAM-01", device_sync=True):
        time.sleep(0.015)  # ~15 ms

    assert len(sync_called) == 2  # start and finish sync
    cam_stats = metrics.stages.get(("detect", "CAM-01"))
    assert cam_stats is not None
    assert cam_stats.count == 1
    p50 = cam_stats.get_percentile_ms(50.0)
    assert 10.0 <= p50 <= 35.0  # allow scheduling jitter tolerance

    # Exception handling: elapsed time is still recorded and exception is re-raised
    caught = False
    try:
        with metrics.stage("preprocess", "CAM-01"):
            time.sleep(0.005)
            raise ValueError("Intentional test fault")
    except ValueError:
        caught = True

    assert caught is True
    pre_stats = metrics.stages.get(("preprocess", "CAM-01"))
    assert pre_stats is not None
    assert pre_stats.count == 1


def test_metrics_counters_and_gauges():
    """Counters must increment monotonically and gauges store latest values."""
    metrics = Metrics()
    metrics.inc("frames_received", 10)
    metrics.inc("frames_received", 5)
    metrics.inc("frames_dropped", 1)

    assert metrics.get_counter("frames_received") == 15
    assert metrics.get_counter("frames_dropped") == 1
    assert metrics.get_counter("unknown", 0) == 0

    metrics.set_gauge("queue_depth", 4.0)
    assert metrics.get_gauge("queue_depth") == 4.0

    snap = metrics.snapshot()
    assert snap["counters"]["frames_received"] == 15
    assert snap["gauges"]["queue_depth"] == 4.0
    assert "timestamp" in snap


def test_frame_trace_properties_and_monotonicity():
    """Verify FrameTrace latency calculations and timestamp monotonic ordering."""
    t0 = 1_000_000_000
    t1 = t0 + 5_000_000   # +5 ms decoded
    t2 = t1 + 3_000_000   # +3 ms pre
    t3 = t2 + 15_000_000  # +15 ms inferred
    t4 = t3 + 4_000_000   # +4 ms tracked
    t5 = t4 + 2_000_000   # +2 ms events
    t6 = t5 + 8_000_000   # +8 ms rendered

    trace = FrameTrace(
        frame_id=101,
        camera_id="CAM-01",
        t_capture_ns=t0,
        t_decoded_ns=t1,
        t_pre_ns=t2,
        t_inferred_ns=t3,
        t_tracked_ns=t4,
        t_events_ns=t5,
        t_rendered_ns=t6,
    )

    assert trace.is_monotonically_ordered is True
    assert abs(trace.processing_latency_ms - 29.0) < 0.001
    assert abs(trace.freshness_ms - 8.0) < 0.001
    assert abs(trace.annotated_latency_ms - 37.0) < 0.001

    d = trace.to_dict()
    assert d["frame_id"] == 101
    assert d["processing_latency_ms"] == 29.0


def test_trace_sampler_rate_and_export():
    """TraceSampler must sample at expected rate and write valid JSONL."""
    with TemporaryDirectory() as tmp_dir:
        trace_file = Path(tmp_dir) / "frame_trace.jsonl"
        sampler = TraceSampler(sample_rate=0.10, output_path=trace_file)

        base_t = time.perf_counter_ns()
        for fid in range(100):
            if sampler.should_sample(fid):
                tr = FrameTrace(
                    frame_id=fid,
                    camera_id="CAM-01",
                    t_capture_ns=base_t,
                    t_decoded_ns=base_t + 1_000_000,
                    t_pre_ns=base_t + 2_000_000,
                    t_inferred_ns=base_t + 12_000_000,
                    t_tracked_ns=base_t + 15_000_000,
                    t_events_ns=base_t + 18_000_000,
                )
                sampler.record_trace(tr)

        sampler.close()

        # At 10% rate over 100 frames, expect exactly 10 samples (frames 0, 10, 20... 90)
        assert len(sampler.traces) == 10
        summary = sampler.compute_summary()
        assert summary["n_samples"] == 10
        assert summary["processing_latency_p50_ms"] == 18.0

        # Verify JSONL lines on disk
        with open(trace_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f]
        assert len(lines) == 10
        assert lines[0]["frame_id"] == 0
        assert lines[9]["frame_id"] == 90
