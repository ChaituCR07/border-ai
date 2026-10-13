import numpy as np
from types import SimpleNamespace
import pytest

from app.anpr.config import (
    AnprConfig,
    ConsensusConfig,
    QualityConfig,
    ScheduleConfig
)
from app.anpr.ocr import ScriptedOcrEngine
from app.anpr.service import AnprService
from app.anpr.types import PlateBox
from app.schemas.tracking import FrameTracks, TrackedObject
from app.schemas.events import PLATE_RECOGNIZED

IMG = np.zeros((240, 320, 3), np.uint8)


class MockLocator:
    def locate(self, crop):
        return [PlateBox(10, 10, 110, 40, 0.9)]


def test_multi_camera_track_id_collision_freedom(tmp_path):
    # Two cameras have vehicles that happen to have the SAME track_id (=10) but different plates
    cfg = AnprConfig(
        schedule=ScheduleConfig(
            min_track_hits=2,
            ocr_every_n_frames=1,
            max_reads_per_track=20,
            min_vehicle_width_px=30,
            border_margin_px=0
        ),
        quality=QualityConfig(min_plate_width_px=10, min_plate_height_px=5, min_sharpness=0),
        consensus=ConsensusConfig(min_reads=3),
        save_crops=False
    )
    # Interleaved OCR responses for CAM_001 and CAM_002
    texts = ["KA01AB1111", "MH12CD2222"] * 20
    events = []
    svc = AnprService(cfg, MockLocator(), ScriptedOcrEngine(texts))
    svc.attach(tmp_path, emit=lambda cid, ev: events.extend(ev), block_when_full=True)

    for i in range(1, 10):
        # CAM_001 vehicle #10
        obj1 = TrackedObject(10, 0, "car", 0.9, 50, 50, 150, 120)
        ft1 = FrameTracks("CAM_001", i, float(i), 320, 240, [obj1])
        svc.submit("CAM_001", ft1, IMG)
        svc.run_pending()

        # CAM_002 vehicle #10
        obj2 = TrackedObject(10, 0, "truck", 0.9, 60, 60, 180, 140)
        ft2 = FrameTracks("CAM_002", i, float(i), 320, 240, [obj2])
        svc.submit("CAM_002", ft2, IMG)
        svc.run_pending()

    # Verify camera snapshot isolation
    snap1 = svc.plates_snapshot("CAM_001")
    snap2 = svc.plates_snapshot("CAM_002")
    assert snap1[10] == "KA01AB1111"
    assert snap2[10] == "MH12CD2222"

    # End track on CAM_001 only
    svc.on_tracks_removed("CAM_001", [SimpleNamespace(track_id=10, last_seen=10.0)])
    svc.run_pending()

    # CAM_001 is finalized, but CAM_002 is still active and unchanged
    assert 10 not in svc.plates_snapshot("CAM_001")
    assert svc.plates_snapshot("CAM_002")[10] == "MH12CD2222"

    # Now end track on CAM_002
    svc.on_tracks_removed("CAM_002", [SimpleNamespace(track_id=10, last_seen=11.0)])
    svc.run_pending()

    assert 10 not in svc.plates_snapshot("CAM_002")
    assert svc.status()["active_vehicles"] == 0

    # Verify both records exist with distinct camera IDs
    records = svc.all_records()
    by_cam = {r.camera_id: r.plate for r in records}
    assert by_cam["CAM_001"] == "KA01AB1111"
    assert by_cam["CAM_002"] == "MH12CD2222"
