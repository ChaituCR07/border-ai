"""Unit tests for consensus strategies, early stop, and funnel monotonicity."""

from evaluation.anpr.consensus import (
    EarlyStopConfig,
    TrackFrameRead,
    VehicleTrack,
    benchmark_strategies,
    evaluate_accuracy_vs_frames,
    replay_track,
    strategy_best_confidence,
    strategy_confidence_weighted_vote,
    strategy_first_valid,
    strategy_majority_vote,
    strategy_positional_consensus,
)
from evaluation.anpr.funnel import VehicleFunnelInput, build_pipeline_funnel


def test_funnel_monotonicity_and_invariants():
    """Verify that funnel stages are strictly monotone and Wilson CIs are valid."""
    inputs = [
        VehicleFunnelInput("v1", True, True, True, True, True, True),
        VehicleFunnelInput("v2", True, True, True, True, False, False),
        VehicleFunnelInput("v3", True, True, True, False, False, False),
        VehicleFunnelInput("v4", True, True, False, False, False, False),
        VehicleFunnelInput("v5", True, False, False, False, False, False),
        VehicleFunnelInput("v6", False, False, False, False, False, False),
        # Vehicle where validation is true but detection is false (must not leak through)
        VehicleFunnelInput("v7", False, True, True, True, True, True),
    ]

    report = build_pipeline_funnel(inputs)
    assert report.total_vehicles == 7

    # Verify counts:
    # 0: all (7)
    # 1: detected (v1, v2, v3, v4, v5) -> 5
    # 2: localized (v1, v2, v3, v4) -> 4
    # 3: ocr (v1, v2, v3) -> 3
    # 4: single exact (v1, v2) -> 2
    # 5: validated (v1) -> 1
    # 6: consensus exact (v1) -> 1
    expected_counts = [7, 5, 4, 3, 2, 1, 1]
    actual_counts = [s.count for s in report.stages]
    assert actual_counts == expected_counts

    # Verify monotonicity: each stage count <= previous stage count (for the detection-to-validation pipeline)
    for i in range(1, 6):
        assert report.stages[i].count <= report.stages[i - 1].count
        assert 0.0 <= report.stages[i].step_retention <= 1.0
        assert 0.0 <= report.stages[i].overall_retention <= 1.0
        lo, hi = report.stages[i].ci_95
        assert 0.0 <= lo <= hi <= 1.0

    # Verify markdown generation
    md = report.to_markdown()
    assert "| Stage | Count |" in md
    assert "Vehicles in evaluation set" in md


def test_strategy_s1_best_confidence():
    """S1 picks highest confidence frame regardless of voting majority."""
    reads = [
        TrackFrameRead(0, "DL01AA0000", 0.98),
        TrackFrameRead(1, "KA01AB1234", 0.60),
        TrackFrameRead(2, "KA01AB1234", 0.65),
    ]
    winner, conf = strategy_best_confidence(reads)
    assert winner == "DL01AA0000"
    assert conf == 0.98


def test_strategy_s2_first_valid():
    """S2 stops on first valid Indian registration plate."""
    reads = [
        TrackFrameRead(0, "NOISY999", 0.70),          # invalid format
        TrackFrameRead(1, "KA01AB1234", 0.92),        # valid standard format
        TrackFrameRead(2, "MH12CD5678", 0.95),        # later valid
    ]
    winner, conf, frames_used = strategy_first_valid(reads)
    assert winner == "KA01AB1234"
    assert conf == 0.92
    assert frames_used == 2


def test_strategy_s3_majority_vote():
    """S3 picks unweighted mode string."""
    reads = [
        TrackFrameRead(0, "KA01AB1234", 0.50),
        TrackFrameRead(1, "KA01AB1234", 0.50),
        TrackFrameRead(2, "DL01AA0000", 0.99),
    ]
    winner, _ = strategy_majority_vote(reads)
    assert winner == "KA01AB1234"


def test_strategy_s4_confidence_weighted():
    """S4 weights votes by confidence."""
    reads = [
        TrackFrameRead(0, "KA01AB1234", 0.20),
        TrackFrameRead(1, "KA01AB1234", 0.20),
        TrackFrameRead(2, "DL01AA0000", 0.95),
    ]
    winner, _ = strategy_confidence_weighted_vote(reads)
    # Sum KA: 0.40, Sum DL: 0.95 -> DL wins
    assert winner == "DL01AA0000"


def test_strategy_s5_positional_character_recovery():
    """S5 positional consensus recovers the true plate from complementary frame errors."""
    # Frame 0: error at index 0 ('0' instead of 'K' -> 0A01AB1234)
    # Frame 1: error at index 9 ('0' instead of '4' -> KA01AB1230)
    # Frame 2: accurate read (KA01AB1234)
    reads = [
        TrackFrameRead(0, "0A01AB1234", 0.85),
        TrackFrameRead(1, "KA01AB1230", 0.85),
        TrackFrameRead(2, "KA01AB1234", 0.92),
    ]
    winner, conf = strategy_positional_consensus(reads)
    assert winner == "KA01AB1234"
    assert conf > 0.50


def test_early_stopping_and_benchmark_replay():
    """Test replay harness with early stopping and accuracy-vs-frames curves."""
    tracks = [
        VehicleTrack(
            vehicle_id="v_ka1",
            gt_plate="KA01AB1234",
            reads=[
                TrackFrameRead(0, "KA01AB1234", 0.92, 0.0),
                TrackFrameRead(1, "KA01AB1234", 0.94, 33.0),
                TrackFrameRead(2, "KA01AB1234", 0.96, 66.0),
                TrackFrameRead(3, "KA01AB1234", 0.95, 100.0),
                TrackFrameRead(4, "KA01AB1234", 0.93, 133.0),
                TrackFrameRead(5, "KA01AB1234", 0.97, 166.0),
            ],
        ),
        VehicleTrack(
            vehicle_id="v_mh1",
            gt_plate="MH12DE4321",
            reads=[
                TrackFrameRead(0, "MH12DE432I", 0.70, 0.0),  # near-miss 'I' vs '1'
                TrackFrameRead(1, "MH12DE4321", 0.91, 33.0),
                TrackFrameRead(2, "MH12DE4321", 0.93, 66.0),
                TrackFrameRead(3, "MH12DE4321", 0.95, 100.0),
            ],
        ),
    ]

    # Run replay with early stopping (min 3 reads, conf 0.85)
    config = EarlyStopConfig(min_reads=3, stable_share=0.60, confidence_thresh=0.85)
    d1 = replay_track(tracks[0], strategy="S5", early_stop=config)
    assert d1.stopped_early is True
    assert d1.frames_used == 3
    assert d1.exact_match is True

    # Benchmark all 5 strategies
    bench = benchmark_strategies(tracks, early_stop=config)
    assert len(bench) == 5
    s5_res = next(r for r in bench if r.strategy == "S5")
    assert s5_res.exact_accuracy == 1.0
    assert s5_res.pct_calls_saved > 0.0

    # Accuracy vs frames curve
    curve = evaluate_accuracy_vs_frames(tracks, budgets=(1, 2, 3, 5), strategy="S5")
    assert len(curve) == 4
    # With 1 frame, v_mh1 had error 'I' vs '1', so accuracy was 0.50
    assert curve[0][1] == 0.50
    # With 2+ frames, positional voting resolved it, so accuracy is 1.0
    assert curve[1][1] == 1.0
    assert curve[2][1] == 1.0
