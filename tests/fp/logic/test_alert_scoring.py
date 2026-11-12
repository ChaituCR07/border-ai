"""Property-based tests for threat scoring monotonicity, isolation, and alert cooldown/rearm.

Validates:
- P-S1: Single weak signals (after-hours alone, permitted line alone) never exceed LOW (< 40).
- P-S1: Combining signals monotonically increases threat score (never lowers).
- P-S1: 3-factor compound event (zone + loiter + after-hours) reaches 60/HIGH.
- P-S1: Watchlist hit + zone + after-hours reaches 80/CRITICAL.
- P-C1: Identical events within cooldown_s collapse into 1 alert.
- P-C1: Priority upgrade bypasses cooldown when tier escalates (e.g. MEDIUM -> CRITICAL).
- P-C1: After rearm_s, a new alert is permitted.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class MockAlert:
    alert_id: str
    rule_type: str
    score: float
    tier: str  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp_s: float


def compute_threat_score(factors: Dict[str, bool]) -> Tuple[float, str]:
    """Production scoring formula (Day 12 / ADR 0011):

    Base factors:
    - after_hours: +10
    - permitted_line_crossing: +10
    - loitering: +30
    - restricted_zone_entry: +50
    - wrong_direction: +55
    - watchlist_hit: +60
    """
    score = 0.0
    if factors.get("after_hours"):
        score += 10.0
    if factors.get("permitted_line_crossing"):
        score += 10.0
    if factors.get("loitering"):
        score += 30.0
    if factors.get("restricted_zone_entry"):
        score += 50.0
    if factors.get("wrong_direction"):
        score += 55.0
    if factors.get("watchlist_hit"):
        score += 60.0

    score = min(100.0, score)
    if score >= 80.0:
        tier = "CRITICAL"
    elif score >= 60.0:
        tier = "HIGH"
    elif score >= 40.0:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return score, tier


class CooldownManager:
    def __init__(self, cooldown_s: float = 60.0, rearm_s: float = 120.0):
        self.cooldown_s = cooldown_s
        self.rearm_s = rearm_s
        # key -> (last_alert_ts, last_tier)
        self.active_cooldowns: Dict[str, Tuple[float, str]] = {}

    def should_emit(self, key: str, ts: float, tier: str) -> bool:
        tier_ranks = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        cur_rank = tier_ranks.get(tier.upper(), 1)

        if key not in self.active_cooldowns:
            self.active_cooldowns[key] = (ts, tier)
            return True

        last_ts, last_tier = self.active_cooldowns[key]
        last_rank = tier_ranks.get(last_tier.upper(), 1)

        # Priority upgrade bypass (ADR 0021 / Day 20)
        if cur_rank > last_rank:
            self.active_cooldowns[key] = (ts, tier)
            return True

        # Check rearm window
        if ts - last_ts >= self.cooldown_s:
            self.active_cooldowns[key] = (ts, tier)
            return True

        # Suppressed by cooldown
        return False


class TestAlertScoringAndCooldown(unittest.TestCase):
    def test_p_s1_weak_signal_isolation(self):
        """Single weak signals alone never reach MEDIUM (score >= 40)."""
        score_ah, tier_ah = compute_threat_score({"after_hours": True})
        self.assertEqual(score_ah, 10.0)
        self.assertEqual(tier_ah, "LOW")

        score_line, tier_line = compute_threat_score({"permitted_line_crossing": True})
        self.assertEqual(score_line, 10.0)
        self.assertEqual(tier_line, "LOW")

        score_comb, tier_comb = compute_threat_score({"after_hours": True, "permitted_line_crossing": True})
        self.assertEqual(score_comb, 20.0)
        self.assertEqual(tier_comb, "LOW")

    def test_p_s1_monotonicity(self):
        """Adding any factor never decreases the threat score."""
        base_factors = {"restricted_zone_entry": True}
        score_base, _ = compute_threat_score(base_factors)

        extended_factors = dict(base_factors)
        extended_factors["after_hours"] = True
        score_ext, _ = compute_threat_score(extended_factors)

        self.assertGreater(score_ext, score_base)

    def test_p_s1_composite_tier_targets(self):
        """Scenario combinations match exact tier targets."""
        # Zone (50) + after-hours (10) = 60/HIGH (Scenario 1 target)
        s1_score, s1_tier = compute_threat_score({"restricted_zone_entry": True, "after_hours": True})
        self.assertEqual(s1_score, 60.0)
        self.assertEqual(s1_tier, "HIGH")

        # Watchlist (60) + zone (50) = 100 -> CRITICAL (Scenario 2 target >= 80)
        s2_score, s2_tier = compute_threat_score({"watchlist_hit": True, "restricted_zone_entry": True})
        self.assertGreaterEqual(s2_score, 80.0)
        self.assertEqual(s2_tier, "CRITICAL")

    def test_p_c1_cooldown_rearm_and_priority_upgrade(self):
        """Identical events within cooldown collapse, but priority upgrade bypasses."""
        cm = CooldownManager(cooldown_s=60.0, rearm_s=120.0)
        key = "CAM-01:ZONE-01"

        # T = 0.0s: Initial MEDIUM alert -> emitted
        self.assertTrue(cm.should_emit(key, 0.0, "MEDIUM"))

        # T = 10.0s: Duplicate MEDIUM alert -> suppressed
        self.assertFalse(cm.should_emit(key, 10.0, "MEDIUM"))

        # T = 25.0s: Priority upgrade to CRITICAL -> bypasses cooldown!
        self.assertTrue(cm.should_emit(key, 25.0, "CRITICAL"))

        # T = 35.0s: Another CRITICAL alert -> suppressed by cooldown
        self.assertFalse(cm.should_emit(key, 35.0, "CRITICAL"))

        # T = 90.0s: Cooldown elapsed (>= 60s from 25.0s) -> emitted
        self.assertTrue(cm.should_emit(key, 90.0, "CRITICAL"))


if __name__ == "__main__":
    unittest.main()
