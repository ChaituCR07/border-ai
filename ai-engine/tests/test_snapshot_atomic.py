import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from app.alerts.snapshot_store import save_snapshot_atomic


class TestSnapshotAtomic(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        if HAS_CV2:
            self.dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        else:
            self.dummy_frame = b"fake_frame_bytes"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_save_snapshot_atomic_success(self):
        rel_path = "snapshots/test_alert.jpg"
        if HAS_CV2:
            ret = save_snapshot_atomic(self.dummy_frame, rel_path, self.tmp_dir, quality=85)
        else:
            mock_cv2 = MagicMock()
            mock_cv2.IMWRITE_JPEG_QUALITY = 1
            mock_cv2.imencode.return_value = (True, MagicMock(tobytes=lambda: b"fake_jpeg_content"))
            with patch("app.alerts.snapshot_store.cv2", mock_cv2):
                ret = save_snapshot_atomic(self.dummy_frame, rel_path, self.tmp_dir, quality=85)

        self.assertEqual(ret, rel_path)
        final_file = os.path.join(self.tmp_dir, rel_path)
        self.assertTrue(os.path.exists(final_file))
        self.assertGreater(os.path.getsize(final_file), 10)

        snap_dir = os.path.dirname(final_file)
        leftovers = [f for f in os.listdir(snap_dir) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            save_snapshot_atomic(self.dummy_frame, "../evil.jpg", self.tmp_dir)

    def test_failure_cleans_up_tmp(self):
        if HAS_CV2:
            with self.assertRaises(Exception):
                save_snapshot_atomic("not_an_image", "snapshots/fail.jpg", self.tmp_dir)
        else:
            mock_cv2 = MagicMock()
            mock_cv2.IMWRITE_JPEG_QUALITY = 1
            mock_cv2.imencode.return_value = (False, None)
            with patch("app.alerts.snapshot_store.cv2", mock_cv2):
                with self.assertRaises(Exception):
                    save_snapshot_atomic(self.dummy_frame, "snapshots/fail.jpg", self.tmp_dir)

        snap_dir = os.path.join(self.tmp_dir, "snapshots")
        if os.path.exists(snap_dir):
            leftovers = [f for f in os.listdir(snap_dir) if f.endswith(".tmp")]
            self.assertEqual(leftovers, [])
            self.assertFalse(os.path.exists(os.path.join(snap_dir, "fail.jpg")))


if __name__ == "__main__":
    unittest.main()
