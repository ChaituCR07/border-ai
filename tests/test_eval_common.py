import json
import os
import tempfile
import unittest
from evaluation.common.hashing import compute_file_sha256
from evaluation.common.bootstrap import bootstrap_ci, bootstrap_ratio_ci
from evaluation.common.manifest import RunManifest
from evaluation.common.tables import format_ci_cell, markdown_table


class TestEvalCommon(unittest.TestCase):
    def test_file_sha256(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("Border-AI-Eval-Test-Content")
            tmp_name = f.name
        try:
            h = compute_file_sha256(tmp_name)
            self.assertIsNotNone(h)
            self.assertEqual(len(h), 64)
            # Re-read same content produces exact same hash
            h2 = compute_file_sha256(tmp_name)
            self.assertEqual(h, h2)
        finally:
            os.remove(tmp_name)

    def test_bootstrap_ci_deterministic_and_bounds(self):
        vals = [0.80, 0.82, 0.85, 0.79, 0.88, 0.84, 0.81, 0.83]
        pt1, lo1, hi1 = bootstrap_ci(vals, n_resamples=500, seed=42)
        pt2, lo2, hi2 = bootstrap_ci(vals, n_resamples=500, seed=42)
        # Deterministic
        self.assertEqual(pt1, pt2)
        self.assertEqual(lo1, lo2)
        self.assertEqual(hi1, hi2)
        # Confidence interval contains point estimate
        self.assertTrue(lo1 <= pt1 <= hi1)

    def test_bootstrap_ratio_ci(self):
        # 10 images with TP and Total GT
        nums = [10, 12, 8, 15, 9, 11, 14, 7, 13, 10]
        dens = [12, 13, 10, 16, 10, 12, 15, 8, 14, 11]
        pt, lo, hi = bootstrap_ratio_ci(nums, dens, n_resamples=500, seed=42)
        expected_ratio = sum(nums) / sum(dens)
        self.assertAlmostEqual(pt, expected_ratio, places=4)
        self.assertTrue(lo <= pt <= hi)

    def test_run_manifest_serialization(self):
        manifest = RunManifest(
            run_id="2026-11-04_test_run",
            task="detection",
            dataset={"name": "coco", "n_images": 100},
            model={"name": "yolov8s", "imgsz": 640},
            inference={"conf": 0.001, "iou": 0.5},
            deployed_thresholds={"person": 0.35, "car": 0.30},
            hardware={"cpu": "arm64", "ram_gb": 16},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = manifest.write_json(tmpdir)
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r") as f:
                data = json.load(f)
            self.assertEqual(data["run_id"], "2026-11-04_test_run")
            self.assertEqual(data["task"], "detection")
            self.assertIn("git_commit", data)

    def test_markdown_tables_formatting(self):
        cell = format_ci_cell(0.854, 0.812, 0.891, is_pct=True)
        self.assertEqual(cell, "85.4% [81.2, 89.1]")

        headers = ["Model", "mAP50", "Recall"]
        rows = [
            ["YOLOv8n", "62.4%", "58.1%"],
            ["YOLOv8s", "71.8%", "68.5%"],
        ]
        table = markdown_table(headers, rows)
        self.assertIn("| Model | mAP50 | Recall |", table)
        self.assertIn("| YOLOv8n | 62.4% | 58.1% |", table)


if __name__ == "__main__":
    unittest.main()
