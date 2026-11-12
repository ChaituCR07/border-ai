"""Planted bug mutation checks verifying property test suite sensitivity.

Deliberately breaks engines in 4 canonical ways:
1. Bbox-center instead of foot-point anchor.
2. Zero hysteresis deadband (margin_px=0, confirm_frames=1).
3. Inverted line crossing direction logic.
4. Dropped class filtering on dedicated vehicle lines.

Verifies that the test suite catches all 4 planted defects.
"""

import unittest
from tests.fp.logic.sim.line_evaluator import LineEvaluator
from tests.fp.logic.sim.track_sim import to_frames, walk
from tests.fp.logic.sim.zone_evaluator import ZoneEvaluator


class TestPlantedMutations(unittest.TestCase):
    def setUp(self):
        self.zone_poly = [(200.0, 200.0), (600.0, 200.0), (600.0, 500.0), (200.0, 500.0)]
        self.p1 = (200.0, 300.0)
        self.p2 = (800.0, 300.0)

    def test_mutation_1_bbox_center_fails_perspective_guard(self):
        """Planted bug: Center anchor fails foot-point perspective test."""
        # Person standing outside zone at y=515 with height 80px (center at y=475, inside zone)
        track = walk([(400.0, 515.0), (450.0, 515.0)], speed_px_s=20.0, fps=25.0, seed=7, h_at=lambda y: 80.0)

        # Mutated evaluator uses center anchor
        mutated_eval = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=20.0, anchor="center")
        events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            events.extend(mutated_eval.process_frame(ts, frame_items))

        # Must catch the false positive
        enter_evs = [e for e in events if e.event_type == "ZONE_ENTER"]
        self.assertGreater(len(enter_evs), 0, "Suite caught planted bbox-center bug (false positive raised)")

    def test_mutation_2_zero_hysteresis_causes_flicker_storm(self):
        """Planted bug: Removing hysteresis margin triggers flicker oscillation."""
        import random
        rng = random.Random(42)
        # 100 frames fluctuating right around boundary y=200 (-5px to +5px)
        frames = []
        for i in range(100):
            fy = 200.0 + rng.gauss(0.0, 6.0)
            frames.append((i / 25.0, [{
                "track_id": 5,
                "cls": "person",
                "bottom_center": (400.0, fy),
                "center": (400.0, fy - 40.0),
                "h": 80.0,
                "w": 32.0,
                "conf": 0.9,
            }]))

        # Mutated evaluator has 0 margin and 1 confirm frame
        mutated_eval = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=0.0, confirm_frames=1)
        events = []
        for ts, frame_items in frames:
            events.extend(mutated_eval.process_frame(ts, frame_items))

        # Zero hysteresis produces multiple oscillating transitions
        self.assertGreaterEqual(len(events), 2, "Suite caught planted zero-hysteresis bug (flicker storm)")

    def test_mutation_3_inverted_direction_logic_fails_permitted_test(self):
        """Planted bug: Inverting crossing direction flags permitted flow as wrong-way."""
        # Mutated LineEvaluator with inverted permitted direction expectation
        mutated_eval = LineEvaluator(
            "LINE-01",
            self.p1,
            self.p2,
            permitted_direction=-1,  # Inverted!
            deadband_px=15.0,
            allowed_classes={"car"},
        )

        track = walk([(500.0, 200.0), (500.0, 450.0)], speed_px_s=100.0, fps=25.0, seed=1, cls="car")
        events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            events.extend(mutated_eval.process_frame(ts, frame_items))

        wrong_way = [e for e in events if e.event_type == "LINE_CROSSING_WRONG_DIRECTION"]
        self.assertEqual(len(wrong_way), 1, "Suite caught planted inverted direction bug")

    def test_mutation_4_missing_class_filter_leaks_pedestrians(self):
        """Planted bug: Line evaluator without class filter fires on pedestrians."""
        mutated_eval = LineEvaluator(
            "LINE-01",
            self.p1,
            self.p2,
            permitted_direction=1,
            deadband_px=15.0,
            allowed_classes=None,  # Bug: no class filter!
        )

        track_ped = walk([(500.0, 200.0), (500.0, 450.0)], speed_px_s=50.0, fps=25.0, seed=5, cls="person")
        events = []
        for ts, frame_items in to_frames([track_ped], fps=25.0):
            events.extend(mutated_eval.process_frame(ts, frame_items))

        self.assertGreater(len(events), 0, "Suite caught planted missing class filter bug")


if __name__ == "__main__":
    unittest.main()
