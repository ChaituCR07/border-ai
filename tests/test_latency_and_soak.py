import os
import unittest
from scripts.measure_latency import compute_percentiles, generate_benchmark_measurements, write_day21_perf_doc
from scripts.soak import sample_telemetry


class TestLatencyAndSoak(unittest.TestCase):
    def test_compute_percentiles(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        p50, p95, p_max = compute_percentiles(values)
        self.assertEqual(p50, 60.0)
        self.assertEqual(p_max, 100.0)
        self.assertTrue(p95 >= 90.0)

    def test_benchmark_conformance_targets(self):
        results = generate_benchmark_measurements()
        for r in results:
            self.assertTrue(r.meets_target, f"Stage {r.stage_name} exceeded p95 target: {r.p95_ms} > {r.target_ms}")

    def test_sample_soak_telemetry_fields(self):
        sample = sample_telemetry(1)
        self.assertIn("rss_mb", sample)
        self.assertIn("open_fds", sample)
        self.assertIn("cpu_pct", sample)
        self.assertIn("timestamp", sample)


if __name__ == "__main__":
    unittest.main()
