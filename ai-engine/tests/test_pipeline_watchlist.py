import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.analytics.engine import RuleEngine
from app.anpr.config import AnprConfig, ConsensusConfig, QualityConfig, ScheduleConfig
from app.anpr.ocr import ScriptedOcrEngine
from app.anpr.service import AnprService
from app.anpr.types import PlateBox
from app.pipeline.pipeline import Pipeline
from app.schemas.detection import Detection, FrameDetections
from app.tracking.tracker import TrackerParams
from app.watchlist.config import WatchlistConfig
from app.watchlist.repo import InMemoryWatchlistRepo
from app.watchlist.service import WatchlistService
from ingestion.camera_manager import CameraManager
from ingestion.sources.file_source import FileSource


class FakeCarDetector:
    model = SimpleNamespace(names={0: "car"})

    def detect_frames(self, frames, conf=None, iou=None):
        return [FrameDetections(f.camera_id, f.frame_id, f.timestamp, f.image.shape[1],
                                f.image.shape[0], [Detection(0, "car", 0.9, 60, 60, 260, 160)], 1.0)
                for f in frames]

    def info(self):
        return {"model": "fake"}


class FakeLocator:
    def locate(self, crop):
        return [PlateBox(20, 40, 120, 80, 0.9)]


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "car.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(60):
        w.write(np.full((240, 320, 3), (i * 3) % 255, np.uint8))
    w.release()
    return path


def anpr_for(plate):
    cfg = AnprConfig(
        schedule=ScheduleConfig(min_track_hits=3, ocr_every_n_frames=2, max_reads_per_track=30,
                                min_vehicle_width_px=50, border_margin_px=0),
        quality=QualityConfig(min_plate_width_px=10, min_plate_height_px=5, min_sharpness=0),
        consensus=ConsensusConfig(min_reads=3), save_crops=False)
    return AnprService(cfg, FakeLocator(), ScriptedOcrEngine([plate]))


def run(tmp_path, sample_video, plate, repo):
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakeCarDetector(), mgr, TrackerParams(), RuleEngine(tmp_path / "zones"),
                 tmp_path / "runs", anpr=anpr_for(plate),
                 watchlist=WatchlistService(repo, WatchlistConfig()))
    p.start()
    assert p.join(timeout=60)
    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    return p, events


@pytest.mark.integration
@pytest.mark.parametrize("plate, listed", [("KA01AB1234", True), ("MH12XY4321", False)])
def test_watchlist_alert_only_for_listed_plates(tmp_path, sample_video, plate, listed):
    repo = InMemoryWatchlistRepo()
    repo.add("VEHICLE", "KA01AB1234", "Watchlist Vehicle 01", "HIGH", actor="test")
    p, events = run(tmp_path, sample_video, plate, repo)

    matches = [e for e in events if e["type"] == "WATCHLIST_MATCH"]
    st = p.status()
    assert st["watchlist"]["dropped"] == 0 if "dropped" in st["watchlist"] else True
    if listed:
        assert len(matches) == 1
        m = matches[0]
        assert m["plate"] == "KA01AB1234" and m["score"] == 90
        assert m["details"]["status"] == "alert" and m["details"]["risk_level"] == "HIGH"
        assert st["watchlist"]["alerts"] == 1
        hits = repo.recent_hits()
        assert len(hits) == 1 and hits[0]["status"] == "alert" and hits[0]["event_id"] == m["event_id"]
    else:
        assert matches == [] and repo.recent_hits() == []


@pytest.mark.integration
def test_pipeline_survives_a_watchlist_database_outage(tmp_path, sample_video):
    repo = InMemoryWatchlistRepo()
    repo.add("VEHICLE", "KA01AB1234", "Watchlist Vehicle 01", "HIGH", actor="test")
    wl = WatchlistService(repo, WatchlistConfig())
    wl.refresh_snapshot()
    repo.fail = True                                    # the database goes away before the run
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakeCarDetector(), mgr, TrackerParams(), RuleEngine(tmp_path / "zones"),
                 tmp_path / "runs", anpr=anpr_for("KA01AB1234"), watchlist=wl)
    wl.refresh_snapshot = lambda: True                  # keep the snapshot taken before the outage
    p.start()
    assert p.join(timeout=60)
    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    assert len([e for e in events if e["type"] == "WATCHLIST_MATCH"]) == 1      # alert still raised
    st = p.status()
    assert st["state"] == "finished" and st["watchlist"]["db_ok"] is False


@pytest.mark.integration
@pytest.mark.db
def test_pipeline_with_a_real_postgres_watchlist(tmp_path, sample_video, pg_repo):
    pg_repo.add("VEHICLE", "KA01AB1234", "Watchlist Vehicle 01", "HIGH", actor="test")
    p, events = run(tmp_path, sample_video, "KA01AB1234", pg_repo)
    assert len([e for e in events if e["type"] == "WATCHLIST_MATCH"]) == 1
    hits = pg_repo.recent_hits()
    assert len(hits) == 1 and hits[0]["status"] == "alert" and hits[0]["score"] == 90
