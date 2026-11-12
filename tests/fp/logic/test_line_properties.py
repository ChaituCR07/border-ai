"""Property-based tests for line crossing, permitted direction, jitter, and class filtering.

Validates:
- P-L1: Permitted direction crossing produces zero direction violations across 20-160 degree angles.
- P-L2: Wrong-way crossing produces exactly one LINE_CROSSING_WRONG_DIRECTION event.
- P-L3: Stationary vehicle on the line with jitter produces zero crossing events.
- P-L4: ID switches during crossing are deduplicated (at most 1 crossing event).
- P-L5: Class filtering suppresses non-vehicle crossings on vehicle lines.
"""

import math
import unittest
from tests.fp.logic.sim.line_evaluator import LineEvaluator
from tests.fp.logic.sim.track_sim import walk, to_frames


class TestLineProperties(unittest.TestCase):
    def setUp(self):
        # Horizontal line from (200, 300) to (800, 300)
        # Normal flow is downward (y increasing, permitted_direction=+1)
        self.p1 = (200.0, 300.0)
        self.p2 = (800.0, 300.0)
        self.line_id = "LINE-01"

    def test_p_l1_permitted_direction(self):
        """P-L1: Vehicle crossing in permitted direction triggers LINE_CROSSING, 0 violations."""
        evaluator = LineEvaluator(
            self.line_id,
            self.p1,
            self.p2,
            permitted_direction=1,
            deadband_px=15.0,
            allowed_classes={"car", "truck"},
        )

        # Cross downward at various angles (angles 30 to 150 degrees)
        for angle_deg in [30, 60, 90, 120, 150]:
            rad = math.radians(angle_deg)
            dx = 150.0 * math.cos(rad)
            dy = 150.0 * math.sin(rad)

            start = (500.0 - dx, 300.0 - dy)
            end = (500.0 + dx, 300.0 + dy)

            track = walk([start, end], speed_px_s=100.0, fps=25.0, seed=angle_deg, cls="car")
            eval_inst = LineEvaluator(
                self.line_id,
                self.p1,
                self.p2,
                permitted_direction=1,
                deadband_px=15.0,
                allowed_classes={"car", "truck"},
            )

            events = []
            for ts, frame_items in to_frames([track], fps=25.0):
                events.extend(eval_inst.process_frame(ts, frame_items))

            violations = [e for e in events if e.event_type == "LINE_CROSSING_WRONG_DIRECTION"]
            permitted = [e for e in events if e.event_type == "LINE_CROSSING"]

            self.assertEqual(len(violations), 0, f"False violation at angle {angle_deg}")
            self.assertEqual(len(permitted), 1, f"Expected 1 permitted crossing at angle {angle_deg}")

    def test_p_l2_wrong_direction(self):
        """P-L2: Vehicle crossing upward against permitted downward flow triggers violation."""
        evaluator = LineEvaluator(
            self.line_id,
            self.p1,
            self.p2,
            permitted_direction=1,
            deadband_px=15.0,
            allowed_classes={"car", "truck"},
        )

        # Crossing upward: y=450 -> y=150
        track = walk([(500.0, 450.0), (500.0, 150.0)], speed_px_s=100.0, fps=25.0, seed=42, cls="truck")
        events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            events.extend(evaluator.process_frame(ts, frame_items))

        violations = [e for e in events if e.event_type == "LINE_CROSSING_WRONG_DIRECTION"]
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].cls, "truck")

    def test_p_l3_stationary_jitter_produces_no_crossings(self):
        """P-L3: Stationary vehicle on the line with jitter within deadband produces 0 crossings."""
        evaluator = LineEvaluator(
            self.line_id,
            self.p1,
            self.p2,
            permitted_direction=1,
            deadband_px=20.0,
            allowed_classes={"car"},
        )

        # Sitting right on line at y=300 with jitter sigma=4.0
        track = walk([(500.0, 300.0), (500.0, 300.0)], speed_px_s=1.0, fps=25.0, seed=12, jitter_sigma=4.0, cls="car")
        while len(track.foot) < 100:
            track.foot.append(track.foot[-1])
            track.box_h.append(track.box_h[-1])
            track.conf.append(track.conf[-1])
            track.present.append(True)

        events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            events.extend(evaluator.process_frame(ts, frame_items))

        self.assertEqual(len(events), 0)

    def test_p_l4_id_switch_deduplication(self):
        """P-L4: ID switch occurring at crossing point is deduplicated into at most 1 event."""
        evaluator = LineEvaluator(
            self.line_id,
            self.p1,
            self.p2,
            permitted_direction=1,
            deadband_px=15.0,
            dedupe_radius_px=60.0,
            dedupe_dt_s=1.5,
            allowed_classes={"car"},
        )

        # First half of track: ID 10 from y=200 to y=330 (crossed line at y=300 and cleared deadband 15px)
        t1 = walk([(500.0, 200.0), (500.0, 330.0)], speed_px_s=100.0, fps=25.0, seed=1, id_=10, cls="car")
        # Second half: ID switches to 11 at (500.0, 335.0) within dedupe radius (5px away) and continues to y=450
        t2 = walk([(500.0, 335.0), (500.0, 450.0)], speed_px_s=100.0, fps=25.0, seed=2, id_=11, cls="car")

        events = []
        # Process t1
        for ts, frame_items in to_frames([t1], fps=25.0):
            events.extend(evaluator.process_frame(ts, frame_items))

        # Process t2 immediately after
        offset_ts = t1.num_frames / 25.0
        for ts, frame_items in to_frames([t2], fps=25.0):
            events.extend(evaluator.process_frame(offset_ts + ts, frame_items))

        # Total crossings must be exactly 1, not 2
        permitted = [e for e in events if e.event_type == "LINE_CROSSING"]
        self.assertEqual(len(permitted), 1)

    def test_p_l5_class_filtering(self):
        """P-L5: Pedestrian crossing vehicle line produces zero line events."""
        evaluator = LineEvaluator(
            self.line_id,
            self.p1,
            self.p2,
            permitted_direction=1,
            allowed_classes={"car", "truck", "bus"},
        )

        track_ped = walk([(500.0, 200.0), (500.0, 400.0)], speed_px_s=50.0, fps=25.0, seed=5, cls="person")
        events = []
        for ts, frame_items in to_frames([track_ped], fps=25.0):
            events.extend(evaluator.process_frame(ts, frame_items))

        self.assertEqual(len(events), 0)


if __name__ == "__main__":
    unittest.main()
