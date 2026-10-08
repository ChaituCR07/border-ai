import json
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.analytics.engine import RuleEngine
from app.pipeline.pipeline import Pipeline
from app.schemas.detection import Detection, FrameDetections
from app.tracking.tracker import TrackerParams
from ingestion.camera_manager import CameraManager
from ingestion.sources.file_source import FileSource

N_FRAMES = 60


class FakeDetector:
    """One person walking straight down the frame at x=160 (frame is 320x240)."""
    model = SimpleNamespace(names={0: "person"})

    def detect_frames(self, frames, conf=None, iou=None):
        out = []
        for f in frames:
            y = 10 + 3 * f.frame_id                       # bottom edge: 13 .. 190
            det = Detection(0, "person", 0.9, 140, y - 60, 180, y)
            out.append(FrameDetections(f.camera_id, f.frame_id, f.timestamp,
                                       f.image.shape[1], f.image.shape[0], [det], 1.0))
        return out

    def info(self):
        return {"model": "fake"}


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "walk.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(N_FRAMES):
        writer.write(np.full((240, 320, 3), (i * 4) % 255, np.uint8))
    writer.release()
    return path


@pytest.fixture
def rules_dir(tmp_path):
    d = tmp_path / "zones"
    d.mkdir()
    (d / "CAM_T.json").write_text(json.dumps({
        "camera_id": "CAM_T",
        "zones": [{"id": "Z1", "name": "Restricted", "type": "restricted",
                   "polygon": [[0.2, 0.6], [0.8, 0.6], [0.8, 1.0], [0.2, 1.0]]}],
        "lines": [{"id": "L1", "name": "Entry", "p1": [0, 0.5], "p2": [1, 0.5]}]}))
    return d


def count_frames(path):
    cap = cv2.VideoCapture(str(path))
    prop = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    n = 0
    while cap.read()[0]:
        n += 1
    return max(prop, n)


def test_offline_pipeline_end_to_end(tmp_path, sample_video, rules_dir):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakeDetector(), mgr, TrackerParams(), RuleEngine(rules_dir), tmp_path / "runs")
    assert p.offline
    p.start()
    assert p.join(timeout=60), "pipeline did not finish"

    st = p.status()
    cam = st["cameras"]["CAM_T"]
    assert st["state"] == "finished"
    assert cam["ingest_dropped"] == 0 and cam["output_dropped"] == 0      # backpressure works
    assert cam["processed"] == cam["rendered"] >= N_FRAMES - 2

    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    crossings = [e for e in events if e["type"] == "LINE_CROSSING"]
    assert len(crossings) == 1 and crossings[0]["direction"] == "IN"
    assert crossings[0]["event"] == "LINE_CROSSING"
    enters = [e for e in events if e["type"] == "ZONE_ENTER"]
    exits = [e for e in events if e["type"] == "ZONE_EXIT"]
    assert len(enters) == 1 and len(exits) == 1                              # paired by the flush
    assert exits[0]["details"]["reason"] == "stream_ended"

    assert count_frames(p.run_dir / "annotated_CAM_T.mp4") == cam["rendered"]
    summary = json.loads((p.run_dir / "summary.json").read_text())
    assert summary["event_counts"]["LINE_CROSSING:L1:IN"] == 1
    manifest = json.loads((p.run_dir / "manifest.json").read_text())
    assert manifest["cameras"]["CAM_T"]["type"] == "FileSource"


def test_live_mode_stops_cleanly(tmp_path, sample_video, rules_dir):
    src = FileSource("CAM_T", sample_video, loop=True, realtime=True)       # paced like a camera
    p = Pipeline(FakeDetector(), CameraManager([src]), TrackerParams(),
                 RuleEngine(rules_dir), tmp_path / "runs", write_video=False)
    assert not p.offline
    p.start()
    time.sleep(1.5)
    assert p.stop(timeout=30), "shutdown deadlocked"
    st = p.status()
    assert st["state"] == "finished"
    assert st["cameras"]["CAM_T"]["processed"] > 5
    assert not (p.run_dir / "annotated_CAM_T.mp4").exists()                 # --no-video honoured


def test_invalid_rules_fail_at_startup(tmp_path, sample_video):
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "CAM_T.json").write_text(json.dumps(
        {"camera_id": "CAM_T", "zones": [{"polygon": [[0, 0], [2, 2], [1, 0]]}]}))
    with pytest.raises(ValueError):
        Pipeline(FakeDetector(), CameraManager([FileSource("CAM_T", sample_video)]),
                 TrackerParams(), RuleEngine(bad), tmp_path / "runs")
