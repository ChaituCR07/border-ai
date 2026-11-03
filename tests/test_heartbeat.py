import json
import time
import unittest
from unittest.mock import MagicMock
from app.observability.heartbeat import HeartbeatPublisher, classify


class TestHeartbeat(unittest.TestCase):
    def test_classify_online(self):
        st = {"connected": True, "last_frame_ts": 100.0}
        self.assertEqual(classify(st, now_s=102.0, stall_after_s=10.0), "ONLINE")

    def test_classify_stalled(self):
        st = {"connected": True, "last_frame_ts": 100.0}
        self.assertEqual(classify(st, now_s=112.0, stall_after_s=10.0), "STALLED")

    def test_classify_reconnecting(self):
        st = {"connected": False, "reconnecting": True}
        self.assertEqual(classify(st, now_s=100.0), "RECONNECTING")

    def test_classify_offline(self):
        st = {"connected": False, "reconnecting": False}
        self.assertEqual(classify(st, now_s=100.0), "OFFLINE")

    def test_heartbeat_publisher_publishes_pipeline(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        cam_data = {
            "CAM-01": {"connected": True, "last_frame_ts": time.time(), "fps": 25.0}
        }
        eng_data = {"build": "v0.3-week3", "device": "mps"}

        pub = HeartbeatPublisher(
            redis_client=mock_redis,
            get_camera_states=lambda: cam_data,
            get_engine_state=lambda: eng_data,
            interval=1.0,
            ttl=15,
        )

        pub.publish_once()

        # Check set called for camera and engine
        self.assertEqual(mock_pipe.set.call_count, 2)
        mock_pipe.execute.assert_called_once()

    def test_heartbeat_swallows_redis_errors(self):
        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = RuntimeError("Redis connection dropped")

        pub = HeartbeatPublisher(
            redis_client=mock_redis,
            get_camera_states=lambda: {},
            get_engine_state=lambda: {},
        )

        # Should not raise
        pub.publish_once()


if __name__ == "__main__":
    unittest.main()
