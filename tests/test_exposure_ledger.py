"""Unit tests for exposure ledger loading, validation, and camera-hour accounting."""

import tempfile
import unittest
from pathlib import Path
from tests.fp.exposure.ledger import ExposureLedger


class TestExposureLedger(unittest.TestCase):
    def test_load_production_ledger(self):
        ledger_path = Path("docs/testing/exposure_ledger.csv")
        ledger = ExposureLedger.load(ledger_path)
        self.assertGreater(len(ledger.entries), 0)

        # Check total hours and splits
        total_h = ledger.total_camera_hours()
        dev_h = ledger.total_camera_hours("dev")
        held_out_h = ledger.total_camera_hours("held-out")

        self.assertAlmostEqual(total_h, dev_h + held_out_h, places=4)
        self.assertAlmostEqual(total_h, 6.25, places=2)
        self.assertAlmostEqual(dev_h, 2.0, places=2)
        self.assertAlmostEqual(held_out_h, 4.25, places=2)

    def test_reject_duplicate_clip_id(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
            f.write(
                "source,clip_id,scene/camera,unique_duration_s,loops,conditions,licence,split,used_for\n"
                "Src,clip_01,CAM-01,100,1,day,Prop,dev,zone\n"
                "Src,clip_01,CAM-01,100,1,day,Prop,held-out,zone\n"
            )
            tmp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                ExposureLedger.load(tmp_path)
            self.assertIn("Duplicate clip_id", str(ctx.exception))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_reject_loops_greater_than_one(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
            f.write(
                "source,clip_id,scene/camera,unique_duration_s,loops,conditions,licence,split,used_for\n"
                "Src,clip_01,CAM-01,100,2,day,Prop,dev,zone\n"
            )
            tmp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                ExposureLedger.load(tmp_path)
            self.assertIn("Non-unit loops", str(ctx.exception))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_reject_invalid_split(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
            f.write(
                "source,clip_id,scene/camera,unique_duration_s,loops,conditions,licence,split,used_for\n"
                "Src,clip_01,CAM-01,100,1,day,Prop,invalid_split,zone\n"
            )
            tmp_path = f.name

        try:
            with self.assertRaises(ValueError) as ctx:
                ExposureLedger.load(tmp_path)
            self.assertIn("Invalid split", str(ctx.exception))
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
