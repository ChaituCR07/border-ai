"""Unit tests for rule mitigations, track quality gates, line debounce, and lookalike filters."""

import unittest
from engine.rules.mitigations import (
    LineDebounceFilter,
    LookalikeMatchFilter,
    MitigationConfig,
    TrackQualityGate,
)


class TestRuleMitigations(unittest.TestCase):
    def setUp(self):
        self.config = MitigationConfig()

    def test_track_quality_gate(self):
        gate = TrackQualityGate(self.config)

        # Hits too low
        self.assertFalse(gate.is_valid_track(hits=2, conf_history=[0.8, 0.8], box_h_px=50.0))

        # Box height too small (< 20px)
        self.assertFalse(gate.is_valid_track(hits=5, conf_history=[0.9, 0.9], box_h_px=15.0))

        # Mean confidence too low (< 0.50)
        self.assertFalse(gate.is_valid_track(hits=5, conf_history=[0.4, 0.45, 0.4], box_h_px=50.0))

        # Valid track
        self.assertTrue(gate.is_valid_track(hits=4, conf_history=[0.85, 0.90, 0.88], box_h_px=65.0))

    def test_line_debounce_filter(self):
        debouncer = LineDebounceFilter(self.config)
        pt = (500.0, 300.0)

        # First crossing allowed
        self.assertTrue(debouncer.should_allow_crossing(ts=10.0, pt=pt, direction=1, track_last_event_ts=-100.0))

        # Duplicate crossing within cooldown (ts=11.0, cooldown=2.0s) -> rejected
        self.assertFalse(debouncer.should_allow_crossing(ts=11.0, pt=pt, direction=1, track_last_event_ts=10.0))

        # Secondary track crossing at almost identical point within 1.0s (ID switch) -> deduplicated
        pt_close = (505.0, 302.0)
        self.assertFalse(debouncer.should_allow_crossing(ts=10.4, pt=pt_close, direction=1, track_last_event_ts=-100.0))

        # Crossing after cooldown (ts=13.0 > 10.0 + 2.0s) -> allowed
        self.assertTrue(debouncer.should_allow_crossing(ts=13.0, pt=pt, direction=1, track_last_event_ts=10.0))

    def test_lookalike_match_filter(self):
        filter_inst = LookalikeMatchFilter(self.config)

        # Exact match always alerts
        allow_exact, reason = filter_inst.should_alert_watchlist_match(
            is_exact_match=True, is_lookalike=False, plate_conf=0.70, agreeing_reads_count=1
        )
        self.assertTrue(allow_exact)
        self.assertEqual(reason, "EXACT_MATCH")

        # Uncorroborated look-alike (single read, conf=0.75 < 0.85) -> suppressed!
        allow_uncorr, reason_uncorr = filter_inst.should_alert_watchlist_match(
            is_exact_match=False, is_lookalike=True, plate_conf=0.75, agreeing_reads_count=1
        )
        self.assertFalse(allow_uncorr)
        self.assertEqual(reason_uncorr, "LOOKALIKE_UNCORROBORATED_SUPPRESSED")

        # Corroborated look-alike via multiple reads (agreeing_reads = 2) -> alerts!
        allow_consensus, reason_cons = filter_inst.should_alert_watchlist_match(
            is_exact_match=False, is_lookalike=True, plate_conf=0.75, agreeing_reads_count=2
        )
        self.assertTrue(allow_consensus)
        self.assertEqual(reason_cons, "LOOKALIKE_CORROBORATED")

        # Corroborated look-alike via high confidence (conf=0.92 >= 0.85) -> alerts!
        allow_hi_conf, reason_hi = filter_inst.should_alert_watchlist_match(
            is_exact_match=False, is_lookalike=True, plate_conf=0.92, agreeing_reads_count=1
        )
        self.assertTrue(allow_hi_conf)
        self.assertEqual(reason_hi, "LOOKALIKE_CORROBORATED")


if __name__ == "__main__":
    unittest.main()
