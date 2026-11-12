"""Unit tests for false-positive triage log and evidence privacy protection."""

import tempfile
import unittest
from pathlib import Path
from tests.fp.tools.evidence import blur_plate_region, create_evidence_package
from tests.fp.tools.fp_log import FpLog


class TestFpLogAndEvidence(unittest.TestCase):
    def test_load_production_fp_log(self):
        log_path = Path("docs/testing/fp_log.csv")
        log = FpLog.load(log_path)

        all_entries = log.entries
        self.assertEqual(len(all_entries), 6)

        # 1 entry is gt_error=yes
        gt_errs = log.gt_errors()
        self.assertEqual(len(gt_errs), 1)
        self.assertEqual(gt_errs[0].fp_id, "FP-004")

        # 5 entries are genuine FPs
        genuine = log.genuine_fps()
        self.assertEqual(len(genuine), 5)

        # Check causes
        causes = log.cause_counts()
        self.assertEqual(causes.get("foot_point_perspective"), 1)
        self.assertEqual(causes.get("tracker_jitter"), 1)
        self.assertNotIn("gt_error", causes)

    def test_reject_invalid_cause(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
            f.write(
                "fp_id,run_id,clip_id,t_clip_s,rule/event,tier,subject,cause,gt_error,status,mitigation_ref,notes\n"
                "FP-999,run_01,clip_01,10.0,ZONE_ENTRY,HIGH,tr1,made_up_cause,no,TRIAGED,none,none\n"
            )
            tmp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                FpLog.load(tmp_path)
            self.assertIn("Invalid cause", str(ctx.exception))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_blur_plate_region(self):
        # 10x10 image with uniform black (0) except a 4x4 white (255) plate in center
        img = [[[0, 0, 0] for _ in range(10)] for _ in range(10)]
        for y in range(3, 7):
            for x in range(3, 7):
                img[y][x] = [200, 200, 200]

        blurred = blur_plate_region(img, (3, 3, 6, 6), block_size=2)
        # Inside plate block, pixels should be averaged
        self.assertEqual(blurred[3][3], [200, 200, 200])

        # Test partial bounding box boundary averaging
        img[3][3] = [100, 100, 100]
        blurred2 = blur_plate_region(img, (3, 3, 4, 4), block_size=2)
        # The 2x2 block (3,3) to (4,4) has one 100 and three 200 => avg 175
        self.assertEqual(blurred2[3][3], [175, 175, 175])

    def test_refuse_evidence_in_forbidden_dirs(self):
        with self.assertRaises(ValueError):
            create_evidence_package(
                fp_id="FP-SEC-01",
                output_dir="/tests/fp/logic",
                metadata={"test": "data"},
                config_hash="abc1234",
            )


if __name__ == "__main__":
    unittest.main()
