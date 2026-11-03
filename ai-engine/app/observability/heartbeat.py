"""
Engine Heartbeat Publisher (ADR 0033).
Publishes engine and per-camera status into Redis with TTL expiry.
Classifies camera streams into ONLINE, RECONNECTING, STALLED, and OFFLINE.
"""

from datetime import datetime, timezone
import json
import logging
import threading
import time
from typing import Any, Callable, Dict

logger = logging.getLogger("heartbeat")


def classify(st: Dict[str, Any], now_s: float, stall_after_s: float = 10.0) -> str:
    """Classifies camera operational state based on connectivity and frame freshness."""
    if not st.get("connected"):
        return "RECONNECTING" if st.get("reconnecting") else "OFFLINE"
    if now_s - st.get("last_frame_ts", 0) > stall_after_s:
        return "STALLED"
    return "ONLINE"


class HeartbeatPublisher(threading.Thread):
    """Background daemon publishing heartbeats to Redis without blocking the main engine."""

    def __init__(
        self,
        redis_client: Any,
        get_camera_states: Callable[[], Dict[str, Dict[str, Any]]],
        get_engine_state: Callable[[], Dict[str, Any]],
        interval: float = 5.0,
        ttl: int = 15,
    ):
        super().__init__(daemon=True, name="HeartbeatPublisher")
        self.r = redis_client
        self.get_camera_states = get_camera_states
        self.get_engine_state = get_engine_state
        self.interval = interval
        self.ttl = ttl
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.wait(self.interval):
            self.publish_once()

    def publish_once(self) -> None:
        try:
            now_dt = datetime.now(timezone.utc).isoformat(timespec="microseconds")
            now_s = time.time()
            cam_states = self.get_camera_states() or {}

            pipe = self.r.pipeline()
            for cam_id, st in cam_states.items():
                st_copy = dict(st)
                st_copy["state"] = classify(st_copy, now_s=now_s)
                key = f"camera:status:{cam_id}"
                pipe.set(key, json.dumps(st_copy), ex=self.ttl)

            eng_state = dict(self.get_engine_state() or {})
            eng_state["at"] = now_dt
            pipe.set("engine:status", json.dumps(eng_state), ex=self.ttl)

            pipe.execute()
        except Exception as e:
            # Heartbeat failure must NEVER crash or block the AI engine
            logger.debug(f"Swallowed heartbeat error: {e}")

    def stop(self) -> None:
        self._stop.set()
