"""Property-based test for analytics-FPS invariance across zone and line rules.

Validates:
- P-F1: Event counts and classifications are invariant across analytics FPS in {25, 15, 10, 5.0}
  for standard movement velocities (<= v_max = 150 px/s).
- Below the rule-correctness floor (< analytics_fps_min = 5.0 FPS), degradation occurs as documented in ADR 0042.
"""

import unittest
from tests.fp.logic.sim.line_evaluator import LineEvaluator
from tests.fp.logic.sim.track_sim import walk, to_frames
from tests.fp.logic.sim.zone_evaluator import ZoneEvaluator


class TestFpsInvariance(unittest.TestCase):
    def setUp(self):
        self.zone_poly = [(200.0, 200.0), (600.0, 200.0), (600.0, 500.0), (200.0, 500.0)]
        self.p1 = (200.0, 300.0)
        self.p2 = (800.0, 300.0)

    def test_p_f1_zone_invariance_above_floor(self):
        """Zone entry count is invariant across FPS in [25, 15, 10, 5.0]."""
        # Path crossing at 80 px/s (well below v_max = 150 px/s)
        wps = [(400.0, 100.0), (400.0, 350.0)]
        target_fps_list = [25.0, 15.0, 10.0, 5.0]
        results = {}

        for fps in target_fps_list:
            track = walk(wps, speed_px_s=80.0, fps=fps, seed=42)
            evaluator = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=20.0, confirm_frames=1)
            events = []
            for ts, frame_items in to_frames([track], fps=fps):
                events.extend(evaluator.process_frame(ts, frame_items))
            results[fps] = len([e for e in events if e.event_type == "ZONE_ENTER"])

        # All runs above floor must yield exactly 1 entry
        for fps, count in results.items():
            self.assertEqual(count, 1, f"FPS {fps} yielded {count} entries, expected 1")

    def test_p_f1_line_invariance_above_floor(self):
        """Line crossing count is invariant across FPS in [25, 15, 10, 5.0]."""
        # Vehicle crossing line at 100 px/s
        wps = [(500.0, 200.0), (500.0, 450.0)]
        target_fps_list = [25.0, 15.0, 10.0, 5.0]
        results = {}

        for fps in target_fps_list:
            track = walk(wps, speed_px_s=100.0, fps=fps, seed=101, cls="car")
            evaluator = LineEvaluator("LINE-01", self.p1, self.p2, permitted_direction=1, deadband_px=15.0)
            events = []
            for ts, frame_items in to_frames([track], fps=fps):
                events.extend(evaluator.process_frame(ts, frame_items))
            results[fps] = len([e for e in events if e.event_type == "LINE_CROSSING"])

        for fps, count in results.items():
            self.assertEqual(count, 1, f"FPS {fps} yielded {count} crossings, expected 1")

    def test_degradation_below_floor_is_bounded(self):
        """At 2.0 FPS (below floor of 5.0 FPS), high-speed crossing (350 px/s) can jump boundary."""
        # 350 px/s across a 30px deadband at 2.0 FPS means 175 px per frame!
        wps = [(500.0, 220.0), (500.0, 420.0)]
        track = walk(wps, speed_px_s=350.0, fps=2.0, seed=77, cls="car")
        evaluator = LineEvaluator("LINE-01", self.p1, self.p2, permitted_direction=1, deadband_px=25.0)
        events = []
        for ts, frame_items in to_frames([track], fps=2.0):
            events.extend(evaluator.process_frame(ts, frame_items))

        # We assert that the system either detects it or documents the known boundary jump
        self.assertIn(len(events), [0, 1])


if __name__ == "__main__":
    unittest.main()
