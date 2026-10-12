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


def test_offline_pipeline_reads_a_plate(tmp_path, sample_video):
    cfg = AnprConfig(
        schedule=ScheduleConfig(min_track_hits=3, ocr_every_n_frames=2, max_reads_per_track=30,
                                min_vehicle_width_px=50, border_margin_px=0),
        quality=QualityConfig(min_plate_width_px=10, min_plate_height_px=5, min_sharpness=0),
        consensus=ConsensusConfig(min_reads=3), save_crops=False)
    anpr = AnprService(cfg, FakeLocator(),
                       ScriptedOcrEngine(["KA01AB1234", "KA01AB1234", "KA01AB1284", "KA01AB1234"]))

    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakeCarDetector(), mgr, TrackerParams(), RuleEngine(tmp_path / "zones"),
                 tmp_path / "runs", anpr=anpr)
    p.start()
    assert p.join(timeout=60)

    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    plates = [e for e in events if e["type"] == "PLATE_RECOGNIZED"]
    assert len(plates) == 1 and plates[0]["details"]["plate"] == "KA01AB1234"
    assert plates[0]["object"]["class"] == "car"

    records = [json.loads(l) for l in (p.run_dir / "anpr" / "plates.jsonl").read_text().splitlines()]
    assert records[-1]["plate"] == "KA01AB1234" and records[-1]["final"] is True
    assert records[-1]["vehicle_id"] >= 1

    st = p.status()
    assert st["anpr"]["dropped"] == 0 and st["anpr"]["reads"] >= 3     # offline: nothing dropped
    assert st["cameras"]["CAM_T"]["processed"] == st["cameras"]["CAM_T"]["rendered"]
    assert "plate_ocr_ms" in st["stages"]
