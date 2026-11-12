"""Unit tests for synthetic track generator."""

import unittest
from tests.fp.logic.sim.track_sim import SimTrack, default_h_at, to_frames, walk


class TestTrackSim(unittest.TestCase):
    def test_deterministic_walk(self):
        wps = [(100.0, 100.0), (300.0, 100.0)]
        t1 = walk(wps, speed_px_s=100.0, fps=25.0, seed=123, jitter_sigma=2.0)
        t2 = walk(wps, speed_px_s=100.0, fps=25.0, seed=123, jitter_sigma=2.0)

        self.assertEqual(t1.num_frames, t2.num_frames)
        self.assertEqual(t1.foot, t2.foot)
        self.assertEqual(t1.present, t2.present)

    def test_dropout_frequency(self):
        wps = [(0.0, 0.0), (1000.0, 0.0)]
        t = walk(wps, speed_px_s=50.0, fps=25.0, seed=42, dropout_p=0.20)
        total = t.num_frames
        dropped = sum(1 for p in t.present if not p)
        rate = dropped / float(total)
        # Check empirical dropout rate close to 0.20
        self.assertAlmostEqual(rate, 0.20, delta=0.05)

    def test_to_frames_generation(self):
        wps = [(50.0, 50.0), (150.0, 50.0)]
        t = walk(wps, speed_px_s=100.0, fps=10.0, seed=99)
        frames = list(to_frames([t], fps=10.0))

        self.assertGreater(len(frames), 5)
        ts, items = frames[0]
        self.assertEqual(ts, 0.0)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["track_id"], 1)
        self.assertEqual(item["cls"], "person")
        self.assertIn("bbox_xyxy", item)
        self.assertIn("bottom_center", item)


if __name__ == "__main__":
    unittest.main()
