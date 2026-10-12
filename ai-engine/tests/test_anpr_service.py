from types import SimpleNamespace

import numpy as np

from app.anpr.config import (AnprConfig, ConsensusConfig, QualityConfig, ScheduleConfig)
from app.anpr.ocr import ScriptedOcrEngine
from app.anpr.service import AnprService
from app.anpr.types import PlateBox
from app.schemas.events import PLATE_RECOGNIZED
from app.schemas.tracking import FrameTracks, TrackedObject

IMG = np.zeros((240, 320, 3), np.uint8)


class FakeLocator:
    def locate(self, crop):
        return [PlateBox(20, 40, 120, 80, 0.9)]


def make(tmp_path, texts, schedule=None, consensus=None, queue_size=32, block=True):
    cfg = AnprConfig(
        schedule=schedule or ScheduleConfig(min_track_hits=2, ocr_every_n_frames=1,
                                            max_reads_per_track=50, min_vehicle_width_px=50,
                                            border_margin_px=0),
        quality=QualityConfig(min_plate_width_px=10, min_plate_height_px=5, min_sharpness=0),
        consensus=consensus or ConsensusConfig(min_reads=3),
        save_crops=False, queue_size=queue_size)
    events = []
    svc = AnprService(cfg, FakeLocator(), ScriptedOcrEngine(texts))
    svc.attach(tmp_path, emit=lambda cid, ev: events.extend(ev), block_when_full=block)
    return svc, events


def frame(i, label="car", tid=1, x1=60, x2=260):
    obj = TrackedObject(tid, 0, label, 0.9, x1, 60, x2, 160)
    obj.stable_class = label
    return FrameTracks("CAM", i, float(i), 320, 240, [obj])


def feed(svc, n, **kw):
    for i in range(1, n + 1):
        svc.submit("CAM", frame(i, **kw), IMG)
        svc.run_pending()


def test_stable_plate_emits_exactly_one_event(tmp_path):
    svc, events = make(tmp_path, ["KA01AB1234", "KA01AB1234", "KA01AB1284"])
    feed(svc, 12)
    svc.stop()
    plate_events = [e for e in events if e.type == PLATE_RECOGNIZED]
    assert len(plate_events) == 1
    assert plate_events[0].details["plate"] == "KA01AB1234"
    assert plate_events[0].details["final"] is False
    recs = svc.all_records()
    assert len(recs) == 1 and recs[0].plate == "KA01AB1234" and recs[0].final


def test_non_vehicle_and_small_vehicle_are_skipped(tmp_path):
    svc, _ = make(tmp_path, ["KA01AB1234"])
    assert svc.submit("CAM", frame(5, label="person"), IMG) == 0
    assert svc.submit("CAM", frame(5, x1=100, x2=140), IMG) == 0          # 40 px wide < 50
    assert svc.stats["skipped_small"] == 1


def test_schedule_every_n_frames(tmp_path):
    sched = ScheduleConfig(min_track_hits=2, ocr_every_n_frames=5, max_reads_per_track=50,
                           min_vehicle_width_px=50, border_margin_px=0)
    svc, _ = make(tmp_path, ["KA01AB1234"], schedule=sched, consensus=ConsensusConfig(min_reads=99))
    feed(svc, 20)
    assert svc.stats["queued"] == 4                         # frames 2, 7, 12, 17


def test_max_reads_cap(tmp_path):
    sched = ScheduleConfig(min_track_hits=2, ocr_every_n_frames=1, max_reads_per_track=3,
                           min_vehicle_width_px=50, border_margin_px=0)
    svc, _ = make(tmp_path, ["KA01AB1234"], schedule=sched, consensus=ConsensusConfig(min_reads=99))
    feed(svc, 20)
    assert svc.stats["queued"] == 3


def test_ocr_stops_once_the_plate_is_stable(tmp_path):
    svc, _ = make(tmp_path, ["KA01AB1234"])
    feed(svc, 30)
    assert svc.stats["queued"] == 3                         # reads at frames 2, 3, 4, then stable


def test_overlay_text_is_provisional_then_stable(tmp_path):
    svc, _ = make(tmp_path, ["KA01AB1234"])
    feed(svc, 2)
    assert svc.plates_snapshot("CAM") == {1: "KA01AB1234?"}
    feed(svc, 4)
    assert svc.plates_snapshot("CAM") == {1: "KA01AB1234"}


def test_vehicle_that_ends_is_finalized_with_a_final_event(tmp_path):
    svc, events = make(tmp_path, ["KA01AB1234"], consensus=ConsensusConfig(min_reads=10))
    feed(svc, 4)                                            # 3 reads, never stable
    assert events == []
    svc.on_tracks_removed("CAM", [SimpleNamespace(track_id=1, last_seen=4.0)])
    assert len(events) == 1 and events[0].details["final"] is True
    assert svc.plates_snapshot("CAM") == {}                 # state cleaned up


def test_finalization_waits_for_queued_reads(tmp_path):
    svc, events = make(tmp_path, ["KA01AB1234"], consensus=ConsensusConfig(min_reads=10))
    svc.submit("CAM", frame(1), IMG)
    svc.submit("CAM", frame(2), IMG)                        # job queued, not yet processed
    svc.on_tracks_removed("CAM", [SimpleNamespace(track_id=1, last_seen=2.0)])
    assert events == [] and svc.status()["active_vehicles"] == 1      # still waiting
    svc.run_pending()
    assert len(events) == 1 and svc.status()["active_vehicles"] == 0


def test_live_mode_drops_the_oldest_jobs_and_keeps_counts_consistent(tmp_path):
    svc, _ = make(tmp_path, ["KA01AB1234"], consensus=ConsensusConfig(min_reads=99),
                  queue_size=2, block=False)
    for i in range(1, 7):                                   # jobs for frames 2..6 pile up unprocessed
        svc.submit("CAM", frame(i), IMG)
    assert svc.stats["dropped"] == 3
    svc.run_pending()
    assert svc._states[("CAM", 1)].pending == 0


def test_junk_text_never_produces_an_event(tmp_path):
    svc, events = make(tmp_path, ["HELLO", "WORLD", "FOO"])
    feed(svc, 8)
    svc.stop()
    assert events == []
