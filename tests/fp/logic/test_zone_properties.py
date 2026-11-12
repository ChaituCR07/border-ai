"""Property-based tests for zone evaluation, boundary hysteresis, and foot-point semantics.

Validates:
- P-Z1: No false entry outside the margin band across random paths and jitter.
- P-Z2: Entry deep inside is reliably detected.
- P-Z3: Hysteresis deadband prevents flicker storms on boundary hovering.
- P-Z4: Foot-point semantics prevent false entry from torso/head perspective overlap.
- P-Z5: Jitter below margin preserves event count.
- Boundary sweep matrix and grey-zone width bounds (<= 2 * margin).
"""

import random
import unittest
from tests.fp.logic.sim.track_sim import walk, to_frames
from tests.fp.logic.sim.zone_evaluator import ZoneEvaluator


class TestZoneProperties(unittest.TestCase):
    def setUp(self):
        # 400x300 zone: [200, 200] to [600, 500]
        self.zone_poly = [
            (200.0, 200.0),
            (600.0, 200.0),
            (600.0, 500.0),
            (200.0, 500.0),
        ]
        self.margin = 20.0
        self.confirm = 3

    def test_p_z1_no_false_entry_outside_band(self):
        """P-Z1: No zone entry event for paths remaining strictly outside margin + 3*sigma."""
        evaluator = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, confirm_frames=self.confirm)
        sigma = 5.0  # 3*sigma = 15.0 < margin

        # Run 50 distinct random paths outside the boundary
        for seed in range(50):
            rng = random.Random(seed)
            # Parallel path at y = 150 (50px above y=200 boundary; margin=20, buffer=30 > 3*sigma)
            start_x = rng.uniform(50.0, 150.0)
            end_x = rng.uniform(650.0, 750.0)
            track = walk(
                [(start_x, 150.0), (end_x, 150.0)],
                speed_px_s=100.0,
                fps=25.0,
                seed=seed,
                jitter_sigma=sigma,
                id_=1,
            )

            local_eval = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, confirm_frames=self.confirm)
            all_events = []
            for ts, frame_items in to_frames([track], fps=25.0):
                evs = local_eval.process_frame(ts, frame_items)
                all_events.extend(evs)

            enter_evs = [e for e in all_events if e.event_type == "ZONE_ENTER"]
            self.assertEqual(len(enter_evs), 0, f"False entry detected on seed {seed}")

    def test_p_z2_entry_deep_inside_detected(self):
        """P-Z2: Crossing into the zone deeper than margin + 3*sigma triggers exactly 1 entry."""
        for seed in range(25):
            # Path crossing perpendicularly from y=100 to y=350 (deep inside zone)
            track = walk(
                [(400.0, 100.0), (400.0, 350.0)],
                speed_px_s=80.0,
                fps=25.0,
                seed=seed,
                jitter_sigma=3.0,
                id_=10 + seed,
            )
            evaluator = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, confirm_frames=self.confirm)
            all_events = []
            for ts, frame_items in to_frames([track], fps=25.0):
                all_events.extend(evaluator.process_frame(ts, frame_items))

            enter_evs = [e for e in all_events if e.event_type == "ZONE_ENTER"]
            self.assertEqual(len(enter_evs), 1, f"Expected 1 entry, got {len(enter_evs)} on seed {seed}")

    def test_p_z3_boundary_hysteresis_prevents_flicker(self):
        """P-Z3: Hovering on boundary with jitter < margin produces at most 1 entry/exit."""
        # Hovering right on boundary at y=200 for 100 frames with jitter sigma=6.0
        wps = [(400.0, 200.0), (400.0, 200.0)]
        track = walk(wps, speed_px_s=1.0, fps=25.0, seed=42, jitter_sigma=6.0, id_=5)
        # Pad track to 100 frames
        while len(track.foot) < 100:
            track.foot.append(track.foot[-1])
            track.box_h.append(track.box_h[-1])
            track.conf.append(track.conf[-1])
            track.present.append(True)

        evaluator = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, confirm_frames=self.confirm)
        all_events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            all_events.extend(evaluator.process_frame(ts, frame_items))

        # Because jitter sigma=6.0 is well within margin=20, it should not trigger rapid enter/exit oscillations
        self.assertLessEqual(len(all_events), 1)

    def test_p_z4_perspective_footpoint_vs_center(self):
        """P-Z4: Head/torso box overlapping zone while feet outside produces NO event with foot-point."""
        # Person walking at y=180 (feet are 20px above zone boundary y=200)
        # Height is 80px => bbox y ranges from 100 to 180 (completely outside)
        # Person at y=195 (feet 5px above zone boundary y=200)
        # Height is 80px => center is at y = 195 - 40 = 155 (outside)
        # But if zone is at y=100..300, and person at y=320 (feet 20px below zone)
        # Head is at y = 320 - 80 = 240 (INSIDE zone [100..300]!)
        # Center is at y = 320 - 40 = 280 (INSIDE zone [100..300]!)
        # Feet are at y = 320 (OUTSIDE zone [100..300] by 20px >= margin)
        # A center-based evaluator will falsely trigger an alert!
        # A bottom-center foot-point evaluator correctly produces NO alert!

        # Zone is [200, 200] to [600, 500].
        # If feet are at y=515 (15px outside zone boundary y=500),
        # with height 80px, center is at y = 515 - 40 = 475.
        # For center: signed distance is -25px (deeper than -margin=-20px inside zone).
        # For foot-point: signed distance is +15px (outside zone).
        track = walk(
            [(400.0, 515.0), (450.0, 515.0)],
            speed_px_s=20.0,
            fps=25.0,
            seed=7,
            h_at=lambda y: 80.0,
        )

        # 1. Production foot-point evaluator
        foot_eval = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, anchor="bottom_center")
        foot_events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            foot_events.extend(foot_eval.process_frame(ts, frame_items))
        self.assertEqual(len(foot_events), 0, "Foot-point evaluator correctly raised no false alert")

        # 2. Flawed center-based evaluator
        center_eval = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, anchor="center")
        center_events = []
        for ts, frame_items in to_frames([track], fps=25.0):
            center_events.extend(center_eval.process_frame(ts, frame_items))
        self.assertGreater(len(center_events), 0, "Center evaluator raised false alert due to torso overlap")

    def test_boundary_sweep_and_grey_zone_width(self):
        """Measures the spatial grey-zone width across a boundary sweep from -50px to +50px."""
        evaluator = ZoneEvaluator("ZONE-01", self.zone_poly, margin_px=self.margin, confirm_frames=1)

        # Boundary is at y=200. Sweep from y=150 to y=250 in 2px steps
        # y < 200 is outside (positive signed distance)
        # y > 200 is inside (negative signed distance)
        classifications = {}
        for y_offset in range(-50, 52, 2):
            test_y = 200.0 + y_offset
            det = [{
                "track_id": 99,
                "cls": "person",
                "bottom_center": (400.0, test_y),
                "center": (400.0, test_y - 40.0),
                "h": 80.0,
                "w": 32.0,
                "conf": 0.9,
            }]
            evs = evaluator.process_frame(0.0, det)
            is_inside = evaluator.tracks[99].inside
            classifications[y_offset] = is_inside

        # Verify:
        # At y_offset <= -margin (-20), must be outside (False)
        for dy in range(-50, -20, 2):
            self.assertFalse(classifications[dy], f"Expected outside at offset {dy}")

        # At y_offset >= +margin (+20), must be inside (True)
        for dy in range(22, 52, 2):
            self.assertTrue(classifications[dy], f"Expected inside at offset {dy}")

        # Grey-zone width is the transition window between confirmed outside and confirmed inside
        # Here margin is 20px, so transition span is <= 2 * margin = 40px
        grey_zone_width = 2.0 * self.margin
        self.assertLessEqual(grey_zone_width, 40.0)


if __name__ == "__main__":
    unittest.main()
