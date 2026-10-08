import time

import cv2
import numpy as np
import pytest

from ingestion.sources.file_source import FileSource
from ingestion.sources.rtsp_source import RtspSource
from ingestion.camera_manager import CameraManager


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "t.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(90):
        writer.write(np.full((240, 320, 3), (i * 2) % 255, np.uint8))
    writer.release()
    return path


def read_all(src, limit=1000):
    frames = []
    while len(frames) < limit:
        f = src.read()
        if f is None:
            break
        frames.append(f)
    return frames


def test_reads_all_frames_and_metadata(sample_video):
    src = FileSource("T1", sample_video, realtime=False)
    assert src.open()
    frames = read_all(src)
    assert len(frames) >= 89
    assert all(f.camera_id == "T1" for f in frames)
    ids = [f.frame_id for f in frames]
    assert ids == sorted(ids) and ids[0] == 1
    assert src.ended
    src.release()


def test_frame_skipping(sample_video):
    src = FileSource("T1", sample_video, target_fps=10, realtime=False)
    assert src.open()
    frames = read_all(src)
    assert 28 <= len(frames) <= 32       # ~90 frames / 3
    src.release()


def test_resize_keeps_aspect(sample_video):
    src = FileSource("T1", sample_video, resize_width=160, realtime=False)
    assert src.open()
    f = src.read()
    assert f.width == 160 and f.height == 120
    src.release()


def test_loop_does_not_end(sample_video):
    src = FileSource("T1", sample_video, loop=True, realtime=False)
    assert src.open()
    frames = read_all(src, limit=200)
    assert len(frames) == 200 and not src.ended
    src.release()


def test_missing_file_fails_cleanly(tmp_path):
    src = FileSource("T1", tmp_path / "nope.mp4")
    assert src.open() is False


def test_multi_camera_manager(sample_video):
    sources = [FileSource(f"C{i}", sample_video, loop=True, realtime=False)
               for i in range(3)]
    mgr = CameraManager(sources)
    mgr.start_all()
    time.sleep(1.0)
    stats = mgr.stats()
    mgr.stop_all()
    assert set(stats) == {"C0", "C1", "C2"}
    assert all(s["frames"] > 0 for s in stats.values())


def test_rtsp_unreachable_does_not_crash():
    src = RtspSource("R1", "rtsp://127.0.0.1:9/none", reconnect_initial=0.2)
    assert src.open() is True
    time.sleep(1.5)
    assert src.read() is None
    assert src.connected is False
    src.release()

def test_offline_file_worker_blocks_instead_of_dropping(sample_video):
    mgr = CameraManager([FileSource("C0", sample_video, realtime=False)], queue_size=2)
    mgr.start_all()
    worker = mgr.workers["C0"]
    got, deadline = 0, time.time() + 20
    while time.time() < deadline:
        f = mgr.get_frame("C0", timeout=0.05)
        if f is not None:
            got += 1
            time.sleep(0.005)                       # slow consumer
        elif worker.status == "ended" and worker.frames.empty():
            break
    mgr.stop_all()
    assert got >= 89 and worker.dropped == 0

