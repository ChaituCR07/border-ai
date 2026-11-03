import unittest
from scripts.sim.cctv_sim import build_ffmpeg_cmd, mask_credentials, CCTVSimulator


class TestCCTVSimulator(unittest.TestCase):
    def test_build_ffmpeg_cmd_structure(self):
        cmd = build_ffmpeg_cmd(
            clip_path="footage/camera_01/normal.mp4",
            rtsp_url="rtsp://localhost:8554/cam01",
            loop=True,
            burn_clock=True,
            freeze=False,
        )
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-re", cmd)
        self.assertIn("-stream_loop", cmd)
        self.assertIn("-1", cmd)
        self.assertIn("-rtsp_transport", cmd)
        self.assertIn("tcp", cmd)
        self.assertEqual(cmd[-1], "rtsp://localhost:8554/cam01")

    def test_build_ffmpeg_cmd_freeze_mode(self):
        cmd = build_ffmpeg_cmd(
            clip_path="footage/camera_01/still.jpg",
            rtsp_url="rtsp://localhost:8554/cam01",
            loop=False,
            burn_clock=True,
            freeze=True,
        )
        self.assertNotIn("-re", cmd)
        self.assertIn("-loop", cmd)
        self.assertIn("1", cmd)

    def test_mask_credentials(self):
        raw_cmd = [
            "ffmpeg",
            "-i",
            "test.mp4",
            "rtsp://rtsp_pub_user:secretPassword123@localhost:8554/cam01",
        ]
        masked = mask_credentials(raw_cmd)
        self.assertNotIn("secretPassword123", masked)
        self.assertIn("rtsp://***:***@localhost:8554/cam01", masked)


if __name__ == "__main__":
    unittest.main()
