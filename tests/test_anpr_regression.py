"""ANPR regression baseline gate on synthetic and test fixtures.

Verifies:
1. Character accuracy >= 95%
2. Plate-level exact accuracy >= 88%
3. Read rate (coverage) >= 92%
4. Look-alike equivalent accuracy >= 90%
5. No degradation relative to evaluation/fixtures/anpr_synth/baseline.json
"""

import json
from pathlib import Path

from evaluation.anpr.datasets.india_anpr import IndiaAnprDataset
from evaluation.anpr.metrics import corpus_metrics, plate_key, score_pair
from evaluation.anpr.predict import OcrPipelineConfig, PipelineEvaluator


def test_anpr_regression_baseline_gate():
    fixture_dir = Path("evaluation/fixtures/anpr_synth")
    labels_path = fixture_dir / "labels.json"
    baseline_path = fixture_dir / "baseline.json"

    assert labels_path.exists(), f"Missing labels fixture at {labels_path}"
    assert baseline_path.exists(), f"Missing baseline record at {baseline_path}"

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    thresholds = baseline.get("gate_thresholds", {})
    min_char_acc = thresholds.get("min_char_accuracy", 0.95)
    min_plate_exact = thresholds.get("min_plate_exact", 0.88)
    min_read_rate = thresholds.get("min_read_rate", 0.92)
    min_lookalike = thresholds.get("min_lookalike_equiv", 0.90)

    dataset = IndiaAnprDataset(labels_path, fixture_dir)
    samples = list(dataset)
    assert len(samples) >= 50, f"Expected at least 50 fixture samples, found {len(samples)}"

    evaluator = PipelineEvaluator(OcrPipelineConfig(mode="M1", position_aware_correction=True))
    results = evaluator.evaluate_batch(samples)

    pairs = [score_pair(s.plate_norm, r.pred_text, plate_key) for s, r in zip(samples, results)]
    corpus = corpus_metrics(pairs)

    # Gate threshold assertions
    assert corpus["char_accuracy"] >= min_char_acc, (
        f"Character accuracy {corpus['char_accuracy']:.4f} regressed below {min_char_acc:.4f}"
    )
    assert corpus["plate_exact"] >= min_plate_exact, (
        f"Plate exact accuracy {corpus['plate_exact']:.4f} regressed below {min_plate_exact:.4f}"
    )
    assert corpus["read_rate"] >= min_read_rate, (
        f"Read rate {corpus['read_rate']:.4f} regressed below {min_read_rate:.4f}"
    )
    assert corpus["lookalike_equiv"] >= min_lookalike, (
        f"Look-alike equivalence {corpus['lookalike_equiv']:.4f} regressed below {min_lookalike:.4f}"
    )

    # Tolerance check against stored baseline (allow at most 0.02 degradation)
    baseline_metrics = baseline.get("metrics", {})
    tolerance = 0.02
    assert corpus["char_accuracy"] >= baseline_metrics["char_accuracy"] - tolerance
    assert corpus["plate_exact"] >= baseline_metrics["plate_exact"] - tolerance
    assert corpus["read_rate"] >= baseline_metrics["read_rate"] - tolerance
