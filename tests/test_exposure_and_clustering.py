"""Unit tests for negative exposure evaluation and soak loop clustering."""

import unittest
from tests.fp.exposure.cluster_loops import cluster_soak_alerts
from tests.fp.exposure.run_exposure import run_exposure_evaluation


class TestExposureAndClustering(unittest.TestCase):
    def test_run_exposure_evaluation_summary(self):
        summary = run_exposure_evaluation(
            ledger_path="docs/testing/exposure_ledger.csv",
            observed_held_out_alerts={"events": 2, "MEDIUM": 1, "HIGH": 0, "CRITICAL": 0},
        )

        self.assertAlmostEqual(summary.held_out_camera_hours, 4.25, places=2)
        self.assertEqual(summary.observed_alerts_high, 0)
        self.assertEqual(summary.rate_high_per_cam_hour, 0.0)
        # Upper bound: 3.689 / 4.25 ~ 0.868
        self.assertAlmostEqual(summary.rate_high_poisson_ci[1], 3.688879 / 4.25, places=3)
        self.assertIn("0 FP alerts", summary.headline_wording)

    def test_cluster_soak_alerts(self):
        # 10 loops of 300s: anomaly repeats at offset 22s +/- 0.5s in every loop
        loop_len = 300.0
        alerts = []
        for i in range(10):
            ts = i * loop_len + 22.0 + (0.2 if i % 2 == 0 else -0.3)
            alerts.append({"camera": "CAM-01", "rule": "ZONE_ENTRY", "timestamp_s": ts})

        # Add one sporadic unrelated anomaly at loop 5, offset 150s
        alerts.append({"camera": "CAM-01", "rule": "ZONE_ENTRY", "timestamp_s": 5 * loop_len + 150.0})

        clusters = cluster_soak_alerts(alerts, loop_period_s=loop_len, tolerance_s=2.0)
        self.assertEqual(len(clusters), 2)

        # Primary cluster: 10 occurrences at ~22.0s
        c1 = [c for c in clusters if abs(c.nominal_offset_s - 22.0) < 1.0][0]
        self.assertEqual(c1.total_occurrences, 10)
        self.assertAlmostEqual(c1.nominal_offset_s, 22.0, delta=0.5)

        # Sporadic cluster: 1 occurrence at 150s
        c2 = [c for c in clusters if abs(c.nominal_offset_s - 150.0) < 1.0][0]
        self.assertEqual(c2.total_occurrences, 1)


if __name__ == "__main__":
    unittest.main()
