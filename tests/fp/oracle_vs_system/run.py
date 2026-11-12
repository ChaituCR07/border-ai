"""Oracle vs System rule evaluation runner and report generator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple
from tests.fp.oracle_vs_system.matching import match_events
from tests.fp.oracle_vs_system.causes import attribute_root_cause
from tests.fp.tools.stats import wilson


@dataclass
class RuleEvaluationResult:
    rule_name: str
    total_system_events: int
    total_oracle_events: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    precision_ci: Tuple[float, float]
    recall: float
    recall_ci: Tuple[float, float]
    cause_breakdown: Dict[str, int]


def evaluate_oracle_vs_system(
    system_events: List[Dict[str, Any]],
    oracle_events: List[Dict[str, Any]],
    gt_frame_objects: List[Dict[str, Any]],
    rule_name: str = "RESTRICTED_ZONE_ENTRY",
    zone_poly: List[Tuple[float, float]] | None = None,
) -> RuleEvaluationResult:
    """Evaluates rule-level precision, recall vs oracle, and attributes root causes for all FPs."""
    matches, unmatched_oracle = match_events(system_events, oracle_events)

    tp_count = sum(1 for m in matches if m.is_tp)
    fp_matches = [m for m in matches if not m.is_tp]
    fp_count = len(fp_matches)
    fn_count = len(unmatched_oracle)

    # Precision = TP / (TP + FP)
    total_sys = tp_count + fp_count
    prec = tp_count / float(total_sys) if total_sys > 0 else 1.0
    prec_ci = wilson(tp_count, total_sys) if total_sys > 0 else (1.0, 1.0)

    # Recall vs Oracle = TP / (TP + FN)
    total_oracle = tp_count + fn_count
    rec = tp_count / float(total_oracle) if total_oracle > 0 else 1.0
    rec_ci = wilson(tp_count, total_oracle) if total_oracle > 0 else (1.0, 1.0)

    # Attribute causes for all FPs
    cause_counts: Dict[str, int] = {}
    for m in fp_matches:
        cause = attribute_root_cause(m.system_event, gt_frame_objects, zone_poly=zone_poly)
        cause_counts[cause] = cause_counts.get(cause, 0) + 1

    return RuleEvaluationResult(
        rule_name=rule_name,
        total_system_events=total_sys,
        total_oracle_events=total_oracle,
        true_positives=tp_count,
        false_positives=fp_count,
        false_negatives=fn_count,
        precision=prec,
        precision_ci=prec_ci,
        recall=rec,
        recall_ci=rec_ci,
        cause_breakdown=cause_counts,
    )
