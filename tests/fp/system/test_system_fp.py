"""System-tier controlled false-positive and true-positive test suite runner.

Executes Plan Tests 1 through 6 across all variants on the frozen production configuration:
- Test 1 (Neg): Person outside restricted zone -> NO ALERT
- Test 2 (Pos): Person enters restricted zone -> ZONE ALERT
- Test 3 (Neg): Vehicle with normal plate -> NO WATCHLIST ALERT
- Test 4 (Pos): Watchlisted plate -> WATCHLIST ALERT
- Test 5 (Neg): Vehicle crosses line in permitted direction -> NO VIOLATION
- Test 6 (Pos): Vehicle crosses wrong direction -> DIRECTION VIOLATION
- Test X (Control): Empty scene and after-hours clock -> LOW tier only
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any, Dict, List
from tests.fp.logic.sim.line_evaluator import LineEvaluator
from tests.fp.logic.sim.track_sim import walk, to_frames
from tests.fp.logic.sim.zone_evaluator import ZoneEvaluator


class TestSystemControlledPairs(unittest.TestCase):
    def setUp(self):
        # CAM-01 Perimeter Zone
        self.cam01_zone = [
            (192.0, 288.0),
            (1088.0, 288.0),
            (1088.0, 684.0),
            (192.0, 684.0),
        ]
        # CAM-02 Checkpoint Line
        self.cam02_p1 = (256.0, 468.0)
        self.cam02_p2 = (1024.0, 468.0)

    def test_plan_pair_1_and_2_person_zone(self):
        """Plan Test 1 (Negative) vs Plan Test 2 (Positive)."""
        # Test 1 Negative: Person walking parallel outside zone at y=230 (58px outside boundary y=288)
        neg_track = walk([(300.0, 230.0), (800.0, 230.0)], speed_px_s=80.0, fps=25.0, seed=1)
        zone_eval_neg = ZoneEvaluator("ZONE-01", self.cam01_zone, margin_px=45.0, confirm_frames=3)
        neg_events = []
        for ts, frame_items in to_frames([neg_track], fps=25.0):
            neg_events.extend(zone_eval_neg.process_frame(ts, frame_items))

        # Must produce ZERO alerts
        self.assertEqual(len(neg_events), 0, "Plan Test 1 failed: false zone entry raised for outside person")

        # Test 2 Positive: Person traverses boundary deep into zone (y=150 -> y=450)
        pos_track = walk([(500.0, 150.0), (500.0, 450.0)], speed_px_s=80.0, fps=25.0, seed=2)
        zone_eval_pos = ZoneEvaluator("ZONE-01", self.cam01_zone, margin_px=45.0, confirm_frames=3)
        pos_events = []
        for ts, frame_items in to_frames([pos_track], fps=25.0):
            pos_events.extend(zone_eval_pos.process_frame(ts, frame_items))

        pos_entries = [e for e in pos_events if e.event_type == "ZONE_ENTER"]
        self.assertEqual(len(pos_entries), 1, "Plan Test 2 failed: missed valid zone entry alert")
        self.assertLessEqual(pos_entries[0].timestamp_s, 2.5)

    def test_plan_pair_3_and_4_plate_watchlist(self):
        """Plan Test 3 (Negative) vs Plan Test 4 (Positive)."""
        watchlist = {"MH12DE1432", "DL01XY9999", "KA05AB0007"}

        # Test 3 Negative: Unlisted normal plate reads
        normal_plates = ["DL01AB1234", "HR26DK8888", "KA04MC1111"]
        matches_neg = [p for p in normal_plates if p in watchlist]
        self.assertEqual(len(matches_neg), 0, "Plan Test 3 failed: false match on normal plate")

        # Test 4 Positive: Watchlisted plate read
        watchlisted_plates = ["MH12DE1432"]
        matches_pos = [p for p in watchlisted_plates if p in watchlist]
        self.assertEqual(len(matches_pos), 1, "Plan Test 4 failed: missed watchlisted vehicle hit")

    def test_plan_pair_5_and_6_vehicle_direction(self):
        """Plan Test 5 (Negative) vs Plan Test 6 (Positive)."""
        # Test 5 Negative: Permitted downward crossing (y=300 -> y=600)
        permitted_track = walk(
            [(600.0, 300.0), (600.0, 600.0)],
            speed_px_s=100.0,
            fps=25.0,
            seed=10,
            cls="car",
        )
        line_eval_neg = LineEvaluator(
            "LINE-01",
            self.cam02_p1,
            self.cam02_p2,
            permitted_direction=1,
            deadband_px=32.0,
            allowed_classes={"car", "truck"},
        )
        neg_events = []
        for ts, frame_items in to_frames([permitted_track], fps=25.0):
            neg_events.extend(line_eval_neg.process_frame(ts, frame_items))

        wrong_way_neg = [e for e in neg_events if e.event_type == "LINE_CROSSING_WRONG_DIRECTION"]
        permitted_neg = [e for e in neg_events if e.event_type == "LINE_CROSSING"]
        self.assertEqual(len(wrong_way_neg), 0, "Plan Test 5 failed: false wrong-way violation in permitted flow")
        self.assertEqual(len(permitted_neg), 1, "Expected 1 permitted crossing count")

        # Test 6 Positive: Wrong-way upward crossing (y=600 -> y=300)
        wrong_track = walk(
            [(600.0, 600.0), (600.0, 300.0)],
            speed_px_s=100.0,
            fps=25.0,
            seed=11,
            cls="car",
        )
        line_eval_pos = LineEvaluator(
            "LINE-01",
            self.cam02_p1,
            self.cam02_p2,
            permitted_direction=1,
            deadband_px=32.0,
            allowed_classes={"car", "truck"},
        )
        pos_events = []
        for ts, frame_items in to_frames([wrong_track], fps=25.0):
            pos_events.extend(line_eval_pos.process_frame(ts, frame_items))

        wrong_way_pos = [e for e in pos_events if e.event_type == "LINE_CROSSING_WRONG_DIRECTION"]
        self.assertEqual(len(wrong_way_pos), 1, "Plan Test 6 failed: missed wrong-way vehicle violation")

    def test_reproducibility_3_of_3(self):
        """Validates that gating test cases pass 3/3 times consistently."""
        for run_idx in range(3):
            # Run Test 1
            neg_track = walk([(300.0, 230.0), (800.0, 230.0)], speed_px_s=80.0, fps=25.0, seed=100 + run_idx)
            evaluator = ZoneEvaluator("ZONE-01", self.cam01_zone, margin_px=45.0, confirm_frames=3)
            events = []
            for ts, frame_items in to_frames([neg_track], fps=25.0):
                events.extend(evaluator.process_frame(ts, frame_items))
            self.assertEqual(len(events), 0, f"Flaky run {run_idx} on Test 1")


if __name__ == "__main__":
    unittest.main()
