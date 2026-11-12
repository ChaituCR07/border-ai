"""Sensitivity Guard verification script.

Ensures that false-positive mitigations and suppression filters do NOT degrade system recall:
- Evaluates Plan positive tests (TP-2, TP-4, TP-6).
- Checks S1 (60/HIGH) and S2 (80/CRITICAL) incident scores.
- Verifies metrics against stored baseline in tests/fp/guard_baseline.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tests.fp.logic.test_alert_scoring import compute_threat_score
from tests.fp.system.test_system_fp import TestSystemControlledPairs


def run_sensitivity_guard(baseline_path: str | Path = "tests/fp/guard_baseline.json") -> bool:
    print("[*] Running Sensitivity Guard Verification Suite...")

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    metrics = baseline["metrics"]
    tolerances = baseline["tolerances"]

    # 1. Evaluate S1 and S2 threat scores
    s1_score, s1_tier = compute_threat_score({"restricted_zone_entry": True, "after_hours": True})
    if s1_score != metrics["scenario_s1_score"] or s1_tier != metrics["scenario_s1_tier"]:
        print(f"[FAIL] S1 threat score regression: got {s1_score}/{s1_tier}, expected {metrics['scenario_s1_score']}/{metrics['scenario_s1_tier']}")
        return False
    print(f"  [PASS] Scenario S1 threat score: {s1_score} ({s1_tier})")

    s2_score, s2_tier = compute_threat_score({"watchlist_hit": True, "restricted_zone_entry": True})
    if s2_score < metrics["scenario_s2_score"] or s2_tier != metrics["scenario_s2_tier"]:
        print(f"[FAIL] S2 threat score regression: got {s2_score}/{s2_tier}")
        return False
    print(f"  [PASS] Scenario S2 threat score: {s2_score} ({s2_tier})")

    # 2. Evaluate positive system tests
    test_case = TestSystemControlledPairs()
    test_case.setUp()

    try:
        test_case.test_plan_pair_1_and_2_person_zone()
        test_case.test_plan_pair_3_and_4_plate_watchlist()
        test_case.test_plan_pair_5_and_6_vehicle_direction()
        print("  [PASS] Plan Positive Tests 2, 4, and 6: 100% recall")
    except AssertionError as e:
        print(f"[FAIL] Positive test assertion failed: {e}")
        return False

    print("\n[OK] Sensitivity Guard Passed: System recall is 100% intact across all positive cases.")
    return True


if __name__ == "__main__":
    ok = run_sensitivity_guard()
    sys.exit(0 if ok else 1)
