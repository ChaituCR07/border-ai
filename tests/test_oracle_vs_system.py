"""Unit tests for oracle-vs-system rule evaluation and cause attribution."""

import unittest
from tests.fp.oracle_vs_system.causes import attribute_root_cause
from tests.fp.oracle_vs_system.gt_zones import generate_negative_band_zones
from tests.fp.oracle_vs_system.matching import match_events
from tests.fp.oracle_vs_system.run import evaluate_oracle_vs_system


class TestOracleVsSystem(unittest.TestCase):
    def test_negative_band_generation_has_no_gt_points(self):
        # A walkway line of GT points along y=300 from x=100 to x=1000
        from tests.fp.logic.sim.oracle import point_in_polygon_2d
        gt_pts = [(float(x), 300.0) for x in range(100, 1000, 20)]
        bands = generate_negative_band_zones(gt_pts, bounds=(1280, 720), d1=20.0, d2=100.0)

        self.assertGreater(len(bands), 0)
        # Check that ZERO GT points fall inside any band polygon
        for poly in bands:
            for gx, gy in gt_pts:
                self.assertFalse(point_in_polygon_2d(poly, (gx, gy)), f"GT point ({gx}, {gy}) was inside negative band {poly}")

    def test_matching_within_tolerance(self):
        sys_events = [
            {"event_type": "ZONE_ENTER", "timestamp_s": 10.2, "anchor_pt": (400.0, 300.0)},
            {"event_type": "ZONE_ENTER", "timestamp_s": 25.0, "anchor_pt": (600.0, 400.0)},
        ]
        oracle_events = [
            {"event_type": "ZONE_ENTER", "timestamp_s": 10.0, "anchor_pt": (405.0, 302.0)},
        ]

        matches, unmatched_oracle = match_events(sys_events, oracle_events, time_tol_s=1.0)
        self.assertEqual(len(matches), 2)
        # First is TP
        self.assertTrue(matches[0].is_tp)
        self.assertAlmostEqual(matches[0].time_diff_s, 0.2, places=3)
        # Second is FP
        self.assertFalse(matches[1].is_tp)
        self.assertEqual(len(unmatched_oracle), 0)

    def test_cause_attribution(self):
        zone_poly = [(200.0, 200.0), (600.0, 200.0), (600.0, 500.0), (200.0, 500.0)]

        # 1. Detector ghost: No GT object within 80px
        ev_ghost = {"event_type": "ZONE_ENTER", "anchor_pt": (900.0, 100.0), "cls": "person"}
        gt_objects = [{"foot": (100.0, 100.0), "cls": "person"}]
        cause_ghost = attribute_root_cause(ev_ghost, gt_objects, zone_poly=zone_poly)
        self.assertEqual(cause_ghost, "detector_ghost")

        # 2. Class confusion: GT exists at location, but is 'car' not 'person'
        ev_conf = {"event_type": "ZONE_ENTER", "anchor_pt": (300.0, 300.0), "cls": "person"}
        gt_car = [{"foot": (305.0, 302.0), "cls": "car"}]
        cause_conf = attribute_root_cause(ev_conf, gt_car, zone_poly=zone_poly)
        self.assertEqual(cause_conf, "class_confusion")

    def test_evaluate_oracle_vs_system_summary(self):
        sys_events = [
            {"event_type": "ZONE_ENTER", "timestamp_s": 5.0, "anchor_pt": (300.0, 300.0), "cls": "person"},
            {"event_type": "ZONE_ENTER", "timestamp_s": 15.0, "anchor_pt": (900.0, 100.0), "cls": "person"},
        ]
        oracle_events = [
            {"event_type": "ZONE_ENTER", "timestamp_s": 5.1, "anchor_pt": (302.0, 301.0), "cls": "person"},
        ]
        gt_frame_objects = [{"foot": (300.0, 300.0), "cls": "person"}]

        res = evaluate_oracle_vs_system(sys_events, oracle_events, gt_frame_objects)
        self.assertEqual(res.true_positives, 1)
        self.assertEqual(res.false_positives, 1)
        self.assertEqual(res.false_negatives, 0)
        self.assertEqual(res.precision, 0.5)
        self.assertEqual(res.recall, 1.0)
        self.assertIn("detector_ghost", res.cause_breakdown)


if __name__ == "__main__":
    unittest.main()
