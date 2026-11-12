"""Unit tests for stress perturbations and camera shift tolerance analysis."""

import unittest
from tests.fp.stress.augment_video import StressConfig, apply_camera_shake, generate_stress_stream
from tests.fp.stress.run_stress import evaluate_camera_shift_tolerance


class TestStressAugmentation(unittest.TestCase):
    def test_apply_camera_shake_translation(self):
        dets = [{
            "track_id": 1,
            "cls": "person",
            "bottom_center": (100.0, 200.0),
            "center": (100.0, 160.0),
            "foot": (100.0, 200.0),
            "bbox_xyxy": (80.0, 120.0, 120.0, 200.0),
        }]

        shifted = apply_camera_shake(dets, (15.0, -10.0))
        d = shifted[0]
        self.assertEqual(d["bottom_center"], (115.0, 190.0))
        self.assertEqual(d["center"], (115.0, 150.0))
        self.assertEqual(d["foot"], (115.0, 190.0))
        self.assertEqual(d["bbox_xyxy"], (95.0, 110.0, 135.0, 190.0))

    def test_generate_stress_stream_dropouts(self):
        frames = [
            (0.0, [{"track_id": 1, "conf": 0.9, "bottom_center": (10.0, 10.0)}]),
            (0.1, [{"track_id": 1, "conf": 0.9, "bottom_center": (12.0, 10.0)}]),
            (0.2, [{"track_id": 1, "conf": 0.9, "bottom_center": (14.0, 10.0)}]),
            (0.3, [{"track_id": 1, "conf": 0.9, "bottom_center": (16.0, 10.0)}]),
            (0.4, [{"track_id": 1, "conf": 0.9, "bottom_center": (18.0, 10.0)}]),
        ]

        cfg = StressConfig(dropout_prob=0.8, confidence_drop=0.20)
        augmented = generate_stress_stream(frames, cfg, seed=123)

        self.assertEqual(len(augmented), 5)
        # Check that confidence dropped on non-dropped frames
        for ts, dets in augmented:
            for d in dets:
                self.assertAlmostEqual(d["conf"], 0.70, places=2)

    def test_camera_shift_tolerance_measurement(self):
        zone_poly = [(200.0, 200.0), (600.0, 200.0), (600.0, 500.0), (200.0, 500.0)]
        res = evaluate_camera_shift_tolerance(zone_poly, margin_px=20.0, max_shift_px=60.0, step_px=10.0)

        self.assertEqual(res["zone_margin_px"], 20.0)
        # Person was at y=175 (25px outside boundary y=200).
        # Inner margin is 20px inside (y=220).
        # Total distance to inner margin is 25 + 20 = 45px!
        # So shifts <= 40px should produce 0 false alerts, while shift >= 50px produces an alert!
        self.assertGreaterEqual(res["max_tolerated_shift_px"], 30.0)
        self.assertLessEqual(res["max_tolerated_shift_px"], 50.0)


if __name__ == "__main__":
    unittest.main()
