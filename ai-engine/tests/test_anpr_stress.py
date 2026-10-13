import concurrent.futures
from types import SimpleNamespace
import numpy as np
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


def make_service(tmp_path, texts, queue_size=32, block=True, min_track_hits=2):
    cfg = AnprConfig(
        schedule=ScheduleConfig(
            min_track_hits=min_track_hits,
            ocr_every_n_frames=1,
            max_reads_per_track=20,
            min_vehicle_width_px=30,
            border_margin_px=0
        ),
        quality=QualityConfig(min_plate_width_px=10, min_plate_height_px=5, min_sharpness=0),
        consensus=ConsensusConfig(min_reads=3),
        save_crops=False,
        queue_size=queue_size
    )
    events = []
    svc = AnprService(cfg, MockLocator(), ScriptedOcrEngine(texts))
    svc.attach(tmp_path, emit=lambda cid, ev: events.extend(ev), block_when_full=block)
    return svc, events


def test_concurrent_multi_vehicle_tracking(tmp_path):
    # 5 concurrent vehicles moving across 15 frames
    vehicles = {
        1: "KA01AB1111",
        2: "MH12CD2222",
        3: "DL04EF3333",
        4: "TN09GH4444",
        5: "GJ01AB5555",
    }
    scripted_texts = []
    for _ in range(20):
        for v_plate in vehicles.values():
            scripted_texts.append(v_plate)

    svc, events = make_service(tmp_path, scripted_texts, queue_size=64, block=True)
    svc.start()

    for frame_id in range(1, 15):
        objs = [
            TrackedObject(tid, 0, "car", 0.9, 50, 50, 150, 120)
            for tid in vehicles.keys()
        ]
        ft = FrameTracks("CAM_001", frame_id, float(frame_id), 320, 240, objs)
        svc.submit("CAM_001", ft, IMG)

    svc.stop(drain=True)

    records = {r.track_id: r.plate for r in svc.all_records()}
    for tid, expected_plate in vehicles.items():
        assert tid in records, f"Vehicle {tid} missing from plate records"
        assert records[tid] == expected_plate, f"Mismatch for vehicle {tid}: expected {expected_plate}, got {records[tid]}"

    plate_events = [e for e in events if e.type == PLATE_RECOGNIZED]
    emitted_plates = {e.track_id: e.details["plate"] for e in plate_events}
    for tid, expected_plate in vehicles.items():
        assert tid in emitted_plates
        assert emitted_plates[tid] == expected_plate


def test_thread_safety_during_active_inference(tmp_path):
    # Worker running in background thread while multiple threads submit and query snapshot
    svc, events = make_service(tmp_path, ["KA01AB1234"] * 100, queue_size=64, block=True)
    svc.start()

    def submitter(worker_id):
        for i in range(1, 25):
            tid = worker_id * 100 + (i % 3)
            obj = TrackedObject(tid, 0, "car", 0.9, 50, 50, 150, 120)
            ft = FrameTracks("CAM_001", i, float(i), 320, 240, [obj])
            svc.submit("CAM_001", ft, IMG)

    def reader():
        snapshots = []
        for _ in range(50):
            snapshots.append(svc.plates_snapshot("CAM_001"))
        return snapshots

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        f_sub1 = executor.submit(submitter, 1)
        f_sub2 = executor.submit(submitter, 2)
        f_sub3 = executor.submit(submitter, 3)
        f_read1 = executor.submit(reader)
        f_read2 = executor.submit(reader)

        f_sub1.result()
        f_sub2.result()
        f_sub3.result()
        f_read1.result()
        f_read2.result()

    svc.stop(drain=True)
    assert svc.status()["errors"] == 0


def test_memory_boundedness_and_cleanup(tmp_path):
    # 50 sequentially passing vehicles that enter, are read, and leave
    svc, events = make_service(tmp_path, ["KA01AB1234"] * 500, queue_size=32, block=True, min_track_hits=1)
    
    for i in range(1, 51):
        obj = TrackedObject(i, 0, "car", 0.9, 50, 50, 150, 120)
        ft1 = FrameTracks("CAM_001", i * 2, float(i * 2), 320, 240, [obj])
        svc.submit("CAM_001", ft1, IMG)
        svc.run_pending()
        
        # Vehicle leaves
        svc.on_tracks_removed("CAM_001", [SimpleNamespace(track_id=i, last_seen=float(i * 2 + 1))])
        svc.run_pending()

    # Verify active vehicle state was completely purged and not leaked
    st = svc.status()
    assert st["active_vehicles"] == 0
    assert len(svc._states) == 0
    # Finished deque recorded all finalized vehicle records
    assert len(svc.finished) == 50
