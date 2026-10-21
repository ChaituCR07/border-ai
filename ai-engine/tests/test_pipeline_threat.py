import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.analytics.engine import RuleEngine
from app.behaviour.engine import BehaviourEngine
from app.pipeline.pipeline import Pipeline
from app.schemas.detection import Detection, FrameDetections
from app.threat.scorer import ThreatScorer
from app.tracking.tracker import TrackerParams
from behaviour_helpers import epoch, make_cfg, make_rule
from ingestion.camera_manager import CameraManager
from ingestion.sources.file_source import FileSource
from threat_helpers import make_scoring

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


def behaviour_rules():
    person = [{"type": "object", "value": ["person"]}]
    return [
        make_rule("R001", person + [{"type": "zone", "zone_type": "restricted"}], "ZONE_VIOLATION", "HIGH", 30),
        make_rule("R002", person + [{"type": "line_crossing", "line": "L1", "expected_direction": "IN"}],
                  "DIRECTION_VIOLATION", "MEDIUM", 20),
        make_rule("R004", person + [{"type": "time", "between": ["22:00", "05:00"]}, {"type": "track_age", "min_s": 0.5}],
                  "AFTER_HOURS_ACTIVITY", "LOW", 10, rearm_s=3600),
    ]


def run(tmp_path, sample_video, zones_dir, clock, snapshots=True):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonWalker(), mgr, TrackerParams(), RuleEngine(zones_dir), tmp_path / "runs",
                 behaviour=BehaviourEngine(make_cfg(behaviour_rules())), scorer=ThreatScorer(make_scoring()),
                 clock_start=epoch(clock), save_snapshots=snapshots)
    p.start()
    assert p.join(timeout=60)
    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    return p, events


@pytest.mark.integration
def test_a_night_walk_into_the_restricted_zone_scores_60_high_with_escalating_alerts(tmp_path, sample_video, zones_dir):
    p, events = run(tmp_path, sample_video, zones_dir, "2026-10-12 02:13:00")
    alerts = [e for e in events if e["type"] == "THREAT_ALERT"]
    assert [a["details"]["level"] for a in alerts] == ["LOW", "MEDIUM", "HIGH"]
    last = alerts[-1]
    assert last["threat_score"] == 60 and last["severity"] == "HIGH"
    assert {c["kind"] for c in last["details"]["contributions"]} == {"zone_violation", "line_crossing", "after_hours"}
    assert p.status()["scoring"]["alerts_by_level"] == {"LOW": 1, "MEDIUM": 1, "HIGH": 1}
    summary = json.loads((p.run_dir / "summary.json").read_text())
    assert summary["event_counts"]["THREAT_ALERT:THREAT"] == 3


@pytest.mark.integration
def test_each_alert_has_an_evidence_snapshot(tmp_path, sample_video, zones_dir):
    p, events = run(tmp_path, sample_video, zones_dir, "2026-10-12 02:13:00")
    for a in (e for e in events if e["type"] == "THREAT_ALERT"):
        path = p.run_dir / a["details"]["snapshot_path"]
        assert path.exists() and path.stat().st_size > 0 and a["details"]["alert_id"] in path.name


@pytest.mark.integration
def test_snapshots_can_be_switched_off(tmp_path, sample_video, zones_dir):
    p, events = run(tmp_path, sample_video, zones_dir, "2026-10-12 02:13:00", snapshots=False)
    assert not (p.run_dir / "snapshots").exists()
    assert all("snapshot_path" not in e["details"] for e in events if e["type"] == "THREAT_ALERT")


@pytest.mark.integration
def test_the_same_walk_by_day_ends_at_50_medium(tmp_path, sample_video, zones_dir):
    _, events = run(tmp_path, sample_video, zones_dir, "2026-10-12 12:13:00")
    alerts = [e for e in events if e["type"] == "THREAT_ALERT"]
    assert alerts[-1]["threat_score"] == 50 and alerts[-1]["details"]["level"] == "MEDIUM"


@pytest.mark.integration
def test_the_pipeline_runs_without_scoring(tmp_path, sample_video, zones_dir):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonWalker(), mgr, TrackerParams(), RuleEngine(zones_dir), tmp_path / "runs")
    p.start()
    assert p.join(timeout=60)
    assert p.status()["scoring"] is None
