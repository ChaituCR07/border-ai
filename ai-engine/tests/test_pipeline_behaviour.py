import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.analytics.engine import RuleEngine
from app.behaviour.engine import BehaviourEngine
from app.pipeline.pipeline import Pipeline
from app.schemas.detection import Detection, FrameDetections
from app.tracking.tracker import TrackerParams
from behaviour_helpers import epoch, make_cfg, make_rule
from ingestion.camera_manager import CameraManager
from ingestion.sources.file_source import FileSource

N_FRAMES = 60


class FakePersonWalker:
    """A person walking straight down a 320x240 frame at x=160: crosses y=120, then enters the bottom zone."""
    model = SimpleNamespace(names={0: "person"})

    def detect_frames(self, frames, conf=None, iou=None):
        out = []
        for f in frames:
            y = 10 + 3 * f.frame_id
            out.append(FrameDetections(f.camera_id, f.frame_id, f.timestamp, f.image.shape[1], f.image.shape[0],
                                       [Detection(0, "person", 0.9, 140, y - 60, 180, y)], 1.0))
        return out

    def info(self):
        return {"model": "fake"}


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "walk.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(N_FRAMES):
        w.write(np.full((240, 320, 3), (i * 4) % 255, np.uint8))
    w.release()
    return path


@pytest.fixture
def zones_dir(tmp_path):
    d = tmp_path / "zones"
    d.mkdir()
    (d / "CAM_T.json").write_text(json.dumps({
        "camera_id": "CAM_T",
        "zones": [{"id": "Z1", "name": "Restricted", "type": "restricted",
                   "polygon": [[0.2, 0.6], [0.8, 0.6], [0.8, 1.0], [0.2, 1.0]]}],
        "lines": [{"id": "L1", "name": "Entry", "p1": [0, 0.5], "p2": [1, 0.5]}]}))
    return d


def rules():
    return [
        make_rule("R001", [{"type": "object", "value": ["person"]}, {"type": "zone", "zone_type": "restricted"}],
                  "ZONE_VIOLATION", "HIGH", 30),
        make_rule("R002", [{"type": "object", "value": ["person"]},
                           {"type": "line_crossing", "line": "L1", "expected_direction": "IN"}],
                  "DIRECTION_VIOLATION", "MEDIUM", 20),
        make_rule("R004", [{"type": "object", "value": ["person"]}, {"type": "time", "between": ["22:00", "05:00"]},
                           {"type": "track_age", "min_s": 0.5}],
                  "AFTER_HOURS_ACTIVITY", "LOW", 10, rearm_s=3600),
    ]


def run(tmp_path, sample_video, zones_dir, clock):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    engine = BehaviourEngine(make_cfg(rules()))
    p = Pipeline(FakePersonWalker(), mgr, TrackerParams(), RuleEngine(zones_dir), tmp_path / "runs",
                 behaviour=engine, clock_start=epoch(clock))
    p.start()
    assert p.join(timeout=60)
    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    return p, events


@pytest.mark.integration
def test_night_time_run_produces_the_expected_behaviour_events(tmp_path, sample_video, zones_dir):
    p, events = run(tmp_path, sample_video, zones_dir, "2026-10-12 02:13:00")
    kinds = [e["type"] for e in events]
    assert "LINE_CROSSING" in kinds and "ZONE_ENTER" in kinds                 # the observations are still there
    assert kinds.count("ZONE_VIOLATION") == 1 and kinds.count("AFTER_HOURS_ACTIVITY") == 1
    assert "DIRECTION_VIOLATION" not in kinds                                  # walking down = IN = expected
    violation = next(e for e in events if e["type"] == "ZONE_VIOLATION")
    assert violation["severity"] == "HIGH" and violation["details"]["points"] == 30
    assert violation["rule"]["kind"] == "behaviour" and violation["details"]["reasons"]
    summary = json.loads((p.run_dir / "summary.json").read_text())
    assert summary["event_counts"]["ZONE_VIOLATION:R001"] == 1
    assert summary["behaviour"]["fired"]["R001"] == 1


@pytest.mark.integration
def test_daytime_run_has_no_after_hours_event(tmp_path, sample_video, zones_dir):
    _, events = run(tmp_path, sample_video, zones_dir, "2026-10-12 12:13:00")
    kinds = [e["type"] for e in events]
    assert "AFTER_HOURS_ACTIVITY" not in kinds and kinds.count("ZONE_VIOLATION") == 1


@pytest.mark.integration
def test_the_pipeline_works_without_the_behaviour_engine(tmp_path, sample_video, zones_dir):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonWalker(), mgr, TrackerParams(), RuleEngine(zones_dir), tmp_path / "runs")
    p.start()
    assert p.join(timeout=60)
    assert p.status()["behaviour"] is None
