"""Unit tests for analytical 2D geometry oracle."""

import unittest
from tests.fp.logic.sim.oracle import (
    min_signed_distance,
    oracle_crossing_direction,
    oracle_never_near,
    oracle_zone_entry,
    point_in_polygon_2d,
)


class TestGeometryOracle(unittest.TestCase):
    def setUp(self):
        # 100x100 square from (100, 100) to (200, 200)
        self.square = [(100.0, 100.0), (200.0, 100.0), (200.0, 200.0), (100.0, 200.0)]

    def test_point_in_polygon(self):
        self.assertTrue(point_in_polygon_2d(self.square, (150.0, 150.0)))
        self.assertFalse(point_in_polygon_2d(self.square, (50.0, 150.0)))
        self.assertFalse(point_in_polygon_2d(self.square, (250.0, 150.0)))

    def test_min_signed_distance(self):
        # Deep inside (center)
        d_in = min_signed_distance(self.square, (150.0, 150.0))
        self.assertAlmostEqual(d_in, -50.0, places=3)

        # Outside by 30px left
        d_out = min_signed_distance(self.square, (70.0, 150.0))
        self.assertAlmostEqual(d_out, 30.0, places=3)

        # On boundary
        d_edge = min_signed_distance(self.square, (100.0, 150.0))
        self.assertAlmostEqual(d_edge, 0.0, places=3)

    def test_oracle_zone_entry_persistence(self):
        # Path passing through zone for only 2 frames, but min_frames=4
        path_brief = [(50.0, 150.0), (150.0, 150.0), (160.0, 150.0), (250.0, 150.0)]
        self.assertFalse(oracle_zone_entry(self.square, path_brief, margin_px=10.0, min_frames=4))

        # Path staying deep inside for 5 frames
        path_sustained = [
            (50.0, 150.0),
            (150.0, 150.0),
            (152.0, 150.0),
            (154.0, 150.0),
            (156.0, 150.0),
            (158.0, 150.0),
            (250.0, 150.0),
        ]
        self.assertTrue(oracle_zone_entry(self.square, path_sustained, margin_px=10.0, min_frames=4))

    def test_oracle_never_near(self):
        # Path always > 20px away from square
        path_far = [(50.0, 50.0), (60.0, 60.0), (70.0, 70.0)]
        self.assertTrue(oracle_never_near(self.square, path_far, margin_px=20.0))

        # Path approaching within 10px
        path_close = [(50.0, 50.0), (95.0, 150.0)]
        self.assertFalse(oracle_never_near(self.square, path_close, margin_px=20.0))

    def test_oracle_crossing_direction(self):
        p1 = (100.0, 100.0)
        p2 = (200.0, 100.0)

        # Downward crossing across horizontal line (from negative y<100 to positive y>100)
        path_down = [(150.0, 80.0), (150.0, 120.0)]
        res_down = oracle_crossing_direction(p1, p2, path_down, deadband_px=5.0)
        self.assertEqual(res_down, 1)

        # Upward crossing across horizontal line
        path_up = [(150.0, 120.0), (150.0, 80.0)]
        res_up = oracle_crossing_direction(p1, p2, path_up, deadband_px=5.0)
        self.assertEqual(res_up, -1)

        # Crossing outside the segment extent (x=300 > 200)
        path_outside = [(300.0, 80.0), (300.0, 120.0)]
        res_out = oracle_crossing_direction(p1, p2, path_outside, deadband_px=5.0)
        self.assertEqual(res_out, 0)


if __name__ == "__main__":
    unittest.main()
