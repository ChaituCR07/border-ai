import json
import queue
import threading
import time

import cv2
import numpy as np

from app.pipeline.metrics import StageTimer
from app.pipeline.queues import put_blocking, put_drop_oldest
from app.pipeline.sinks import FrameHub, JsonlSink, VideoSink


def test_put_drop_oldest_keeps_the_newest():
    q = queue.Queue(maxsize=2)
    assert put_drop_oldest(q, 1) is False
    assert put_drop_oldest(q, 2) is False
    assert put_drop_oldest(q, 3) is True
    assert [q.get(), q.get()] == [2, 3]


def test_put_blocking_returns_false_when_stopped():
    q = queue.Queue(maxsize=1)
    q.put("x")
    stop = threading.Event()
    stop.set()
    assert put_blocking(q, "y", stop, poll_s=0.01) is False


def test_put_blocking_succeeds_when_room_appears():
    q = queue.Queue(maxsize=1)
    q.put("x")
    threading.Timer(0.1, q.get).start()
    assert put_blocking(q, "y", threading.Event(), poll_s=0.02) is True


def test_stage_timer_summary():
    t = StageTimer(window=3)
    for ms in (1, 2, 3, 100):
        t.record("detect", ms)
    s = t.summary()["detect"]
    assert s["n"] == 4 and s["mean_all_ms"] == 26.5       # whole run
    assert s["max_ms"] == 100 and s["mean_ms"] > 30       # recent window only (2, 3, 100)


def test_jsonl_sink_writes_lines_and_keeps_recent(tmp_path):
    sink = JsonlSink(tmp_path / "e.jsonl", keep_recent=2)
    sink.write({"camera_id": "A", "n": 1})
    sink.write({"camera_id": "B", "n": 2})
    sink.write({"camera_id": "A", "n": 3})
    sink.close()
    lines = [json.loads(l) for l in (tmp_path / "e.jsonl").read_text().splitlines()]
    assert [r["n"] for r in lines] == [1, 2, 3]
    assert [r["n"] for r in sink.recent_records()] == [3, 2]            # newest first, ring of 2
    assert [r["n"] for r in sink.recent_records(camera_id="A")] == [3]
    sink.write({"camera_id": "A", "n": 4})                                # after close: ignored
    assert sink.count == 3


def test_video_sink_keeps_first_frame_size(tmp_path):
    path = tmp_path / "v.mp4"
    sink = VideoSink(path, fps=10)
    for _ in range(5):
        sink.write(np.zeros((48, 64, 3), np.uint8))
    sink.write(np.zeros((24, 32, 3), np.uint8))            # other size: resized, not dropped
    sink.close()
    cap, n = cv2.VideoCapture(str(path)), 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        assert img.shape[:2] == (48, 64)
        n += 1
    assert max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), n) == 6 == sink.frames


def test_frame_hub_jpeg_is_cached_per_sequence():
    hub = FrameHub()
    img = np.zeros((48, 64, 3), np.uint8)
    hub.put("C1", img)
    seq = hub.seq("C1")
    a = hub.jpeg("C1", seq, hub.latest_image("C1"))
    b = hub.jpeg("C1", seq, img)
    assert a[:2] == b"\xff\xd8" and a is b


def test_frame_hub_wait_for_new_times_out_then_wakes():
    hub = FrameHub()
    assert hub.wait_for_new("C1", 0, timeout=0.05) == (None, None)
    threading.Timer(0.1, hub.put, args=("C1", np.zeros((8, 8, 3), np.uint8))).start()
    seq, image = hub.wait_for_new("C1", 0, timeout=2.0)
    assert seq == 1 and image is not None
