import logging
import queue
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.anpr.config import AnprConfig
from app.anpr.consensus import ConsensusResult, PlateConsensus
from app.anpr.plate_format import PlateFormats
from app.anpr.preprocess import crop_with_pad, plate_quality, preprocess
from app.anpr.types import PlateRead, PlateRecord
from app.pipeline.metrics import StageTimer
from app.pipeline.sinks import JsonlSink
from app.schemas.events import PLATE_RECOGNIZED, Event

log = logging.getLogger("anpr")


@dataclass
class OcrJob:
    camera_id: str
    track_id: int
    frame_id: int
    timestamp: float
    vehicle_crop: np.ndarray
    vehicle_class: str
    bbox: Tuple[float, float, float, float]


@dataclass
class _TrackState:
    camera_id: str
    track_id: int
    consensus: PlateConsensus
    vehicle_class: str = "vehicle"
    first_ts: float = 0.0
    last_ts: float = 0.0
    last_frame_id: int = 0
    last_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    frames_seen: int = 0
    last_sched_frame: int = -10 ** 9
    reads_scheduled: int = 0
    pending: int = 0                      # jobs queued or running for this vehicle
    stable: bool = False
    ended: bool = False
    emitted_text: Optional[str] = None
    display: str = ""


def _crop(image: np.ndarray, bbox, margin: float) -> np.ndarray:
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    xa, ya = max(0, int(x1 - mx)), max(0, int(y1 - my))
    xb, yb = min(w, int(x2 + mx)), min(h, int(y2 + my))
    return image[ya:yb, xa:xb].copy()


class AnprService:
    def __init__(self, cfg: AnprConfig, locator, ocr):
        self.cfg = cfg
        self.locator = locator
        self.ocr = ocr
        self.formats = PlateFormats(cfg.formats)
        self._vehicle_classes = set(cfg.vehicle_classes)

        self._lock = threading.RLock()
        self._states: Dict[Tuple[str, int], _TrackState] = {}
        self.finished: Deque[PlateRecord] = deque(maxlen=1000)
        self.stats: Counter = Counter()
        self.timers = StageTimer()

        self._q: Optional[queue.Queue] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._emit: Callable[[str, List[Event]], None] = lambda cid, events: None
        self.block_when_full = False
        self.out_dir: Optional[Path] = None
        self.records_sink: Optional[JsonlSink] = None

    # ------------------------------------------------------------------ setup / lifecycle
    def attach(self, out_dir: Path, emit=None, timers: Optional[StageTimer] = None,
               block_when_full: bool = False) -> "AnprService":
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.records_sink = JsonlSink(self.out_dir / "plates.jsonl")
        if emit is not None:
            self._emit = emit
        if timers is not None:
            self.timers = timers
        self.block_when_full = block_when_full
        self._q = queue.Queue(maxsize=self.cfg.queue_size)
        return self

    def start(self) -> None:
        self._thread = threading.Thread(target=self._worker, name="anpr-worker", daemon=True)
        self._thread.start()

    def stop(self, drain: bool = True, timeout: float = 60.0) -> None:
        """Finish queued reads (when drain), finalize every vehicle still open, and close files."""
        deadline = time.time() + timeout
        if drain:
            if self._thread is None:
                self.run_pending()                          # synchronous mode
            else:
                while self._q.unfinished_tasks and time.time() < deadline:
                    time.sleep(0.05)
        self._stop.set()
        if self._thread is not None:
            try:
                self._q.put(None, timeout=5)
            except queue.Full:
                pass
            self._thread.join(timeout=10)

        by_camera: Dict[str, List[Event]] = {}
        with self._lock:
            for st in list(self._states.values()):
                by_camera.setdefault(st.camera_id, []).extend(self._finalize_locked(st))
        for cid, events in by_camera.items():
            self._emit_events(cid, events)
        if self.records_sink is not None:
            self.records_sink.close()

    # ------------------------------------------------------------------ called by the pipeline
    def submit(self, camera_id: str, ft, image: np.ndarray) -> int:
        """Look at this frame's tracks and queue OCR jobs for vehicles that are due. Returns the job count."""
        H, W = image.shape[:2]
        sched = self.cfg.schedule
        jobs: List[OcrJob] = []
        with self._lock:
            for o in ft.tracks:
                if o.label not in self._vehicle_classes:
                    continue
                key = (camera_id, o.track_id)
                st = self._states.get(key)
                if st is None:
                    st = _TrackState(camera_id, o.track_id, self._new_consensus(), first_ts=ft.timestamp)
                    self._states[key] = st
                st.frames_seen += 1
                st.last_ts, st.last_frame_id = ft.timestamp, ft.frame_id
                st.last_bbox, st.vehicle_class = o.bbox, o.label

                if st.stable or st.reads_scheduled >= sched.max_reads_per_track:
                    continue
                if (o.x2 - o.x1) < sched.min_vehicle_width_px:
                    self.stats["skipped_small"] += 1
                    continue
                m = sched.border_margin_px
                if m and (o.x1 < m or o.y1 < m or o.x2 > W - m or o.y2 > H - m):
                    self.stats["skipped_border"] += 1
                    continue
                if st.frames_seen < sched.min_track_hits:
                    continue
                if st.frames_seen - st.last_sched_frame < sched.ocr_every_n_frames:
                    continue
                crop = _crop(image, o.bbox, sched.crop_margin)
                if crop.size == 0:
                    continue
                st.last_sched_frame = st.frames_seen
                st.reads_scheduled += 1
                st.pending += 1
                jobs.append(OcrJob(camera_id, o.track_id, ft.frame_id, ft.timestamp, crop,
                                   o.label, tuple(o.bbox)))
        for job in jobs:
            self._enqueue(job)
        return len(jobs)

    def on_tracks_removed(self, camera_id: str, tracks) -> None:
        """Tell the service which vehicle tracks the tracker has finally removed."""
        events: List[Event] = []
        with self._lock:
            for t in tracks:
                st = self._states.get((camera_id, t.track_id))
                if st is None:
                    continue
                st.ended = True
                st.last_ts = max(st.last_ts, t.last_seen)
                if st.pending <= 0:
                    events += self._finalize_locked(st)
        self._emit_events(camera_id, events)

    def plates_snapshot(self, camera_id: str) -> Dict[int, str]:
        with self._lock:
            return {tid: st.display for (cid, tid), st in self._states.items()
                    if cid == camera_id and st.display}

    def all_records(self) -> List[PlateRecord]:
        with self._lock:
            return list(self.finished)

    def status(self) -> dict:
        with self._lock:
            active, finished = len(self._states), len(self.finished)
            stats = dict(self.stats)
        stats.setdefault("dropped", 0)
        stats.setdefault("reads", 0)
        stats.setdefault("errors", 0)
        return {"queue": self._q.qsize() if self._q is not None else 0,
                "active_vehicles": active, "finished": finished, **stats}

    # ------------------------------------------------------------------ queue and worker
    def _new_consensus(self) -> PlateConsensus:
        cc = self.cfg.consensus

        def normalize(text: str):
            c = self.formats.check(text)
            return c.text, c.level

        return PlateConsensus(normalize, cc.min_reads, cc.stable_share)

    def _enqueue(self, job: OcrJob) -> None:
        if self.block_when_full:
            while not self._stop.is_set():
                try:
                    self._q.put(job, timeout=0.1)
                    self._inc("queued")
                    return
                except queue.Full:
                    continue
            self._complete(job, dropped=True)
            return
        while True:                                           # live: drop the oldest job
            try:
                self._q.put_nowait(job)
                self._inc("queued")
                return
            except queue.Full:
                try:
                    old = self._q.get_nowait()
                except queue.Empty:
                    continue
                self._q.task_done()
                self._complete(old, dropped=True)

    def _worker(self) -> None:
        while True:
            job = self._q.get()
            try:
                if job is None:
                    return
                self._handle(job)
            finally:
                self._q.task_done()

    def run_pending(self) -> int:
        """Process queued jobs in the calling thread (used when no worker thread is running)."""
        n = 0
        while True:
            try:
                job = self._q.get_nowait()
            except queue.Empty:
                return n
            try:
                if job is not None:
                    self._handle(job)
                    n += 1
            finally:
                self._q.task_done()

    def _handle(self, job: OcrJob) -> None:
        try:
            events = self._process(job)
        except Exception:
            log.exception("ANPR job failed")
            self._inc("errors")
            events = []
        self._emit_events(job.camera_id, events)
        self._complete(job)

    def _complete(self, job: OcrJob, dropped: bool = False) -> None:
        events: List[Event] = []
        with self._lock:
            if dropped:
                self.stats["dropped"] += 1
            st = self._states.get((job.camera_id, job.track_id))
            if st is not None:
                st.pending -= 1
                if st.ended and st.pending <= 0:
                    events = self._finalize_locked(st)
        self._emit_events(job.camera_id, events)

    # ------------------------------------------------------------------ the OCR job itself
    def _process(self, job: OcrJob) -> List[Event]:
        cfg = self.cfg

        t0 = time.perf_counter()
        boxes = self.locator.locate(job.vehicle_crop)
        self._time("plate_locate_ms", t0)
        if not boxes:
            self._inc("no_plate")
            return []

        plate = crop_with_pad(job.vehicle_crop, boxes[0], cfg.crop_pad)
        quality = plate_quality(plate, cfg.quality)
        if not quality.ok:
            self._inc("low_quality")
            return []

        t1 = time.perf_counter()
        prepared = preprocess(plate, cfg.preprocess, cfg.preprocess_height)
        self._time("plate_preprocess_ms", t1)

        t2 = time.perf_counter()
        result = self.ocr.read(prepared)
        self._time("plate_ocr_ms", t2)
        if not result.text or result.confidence < cfg.ocr.min_confidence:
            self._inc("ocr_empty")
            return []

        check = self.formats.check(result.text)
        weight = result.confidence * (0.5 + 0.5 * quality.score) * self._level_weight(check.level)
        if weight <= 0:
            self._inc("rejected")
            return []

        read = PlateRead(text=check.text, raw=result.text, confidence=result.confidence,
                         weight=weight, quality=quality.score, level=check.level,
                         frame_id=job.frame_id, timestamp=job.timestamp, crop=plate)
        with self._lock:
            st = self._states.get((job.camera_id, job.track_id))
            if st is None:
                return []
            st.consensus.add(read)
            self.stats["reads"] += 1
            best = st.consensus.best()
            events: List[Event] = []
            if not st.stable and st.consensus.is_stable(best):
                events = self._publish_stable_locked(st, best)
            st.display = best.text + ("" if st.stable else "?")
            return events

    def _level_weight(self, level: str) -> float:
        cc = self.cfg.consensus
        return {"strict": 1.0, "loose": cc.loose_weight, "invalid": cc.invalid_weight}[level]

    # ------------------------------------------------------------------ records and events (lock held)
    def _make_record(self, st: _TrackState, best: ConsensusResult, final: bool) -> PlateRecord:
        log_ = ([(r.text, r.confidence) for r in st.consensus.reads]
                if self.cfg.keep_read_log else [])
        return PlateRecord(
            camera_id=st.camera_id, track_id=st.track_id, plate=best.text,
            confidence=best.confidence, reads=best.n_reads, votes=best.votes,
            agreement=best.agreement, format_level=best.level, final=final,
            vehicle_class=st.vehicle_class, first_seen=st.first_ts, last_seen=st.last_ts,
            method=best.method, read_log=log_)

    def _event(self, st: _TrackState, rec: PlateRecord) -> Event:
        return Event(
            type=PLATE_RECOGNIZED, camera_id=st.camera_id, timestamp=st.last_ts,
            frame_id=st.last_frame_id, track_id=st.track_id, object_class=st.vehicle_class,
            confidence=rec.confidence, bbox=st.last_bbox, rule_id="ANPR",
            rule_name="Plate recognition", rule_kind="anpr", rule_type="plate",
            details={"plate": rec.plate, "reads": rec.reads, "votes": rec.votes,
                     "agreement": round(rec.agreement, 3), "format": rec.format_level,
                     "method": rec.method, "final": rec.final})

    def _publish_stable_locked(self, st: _TrackState, best: ConsensusResult) -> List[Event]:
        st.stable = True
        rec = self._make_record(st, best, final=False)
        st.emitted_text = best.text
        self._save_best_crop(st)
        if self.records_sink is not None:
            self.records_sink.write(rec.to_dict())
        return [self._event(st, rec)]

    def _finalize_locked(self, st: _TrackState) -> List[Event]:
        self._states.pop((st.camera_id, st.track_id), None)
        best = st.consensus.best()
        if best is None:
            return []
        rec = self._make_record(st, best, final=True)
        events: List[Event] = []
        worth = (best.level in ("strict", "loose")
                 and best.confidence >= self.cfg.consensus.final_min_confidence)
        if best.text != st.emitted_text and worth:
            events.append(self._event(st, rec))
            st.emitted_text = best.text
            self._save_best_crop(st)
        self.finished.append(rec)
        if self.records_sink is not None:
            self.records_sink.write(rec.to_dict())
        return events

    def _save_best_crop(self, st: _TrackState) -> None:
        if not self.cfg.save_crops or self.out_dir is None:
            return
        crop = st.consensus.best_crop()
        if crop is not None:
            folder = self.out_dir / "plates"
            folder.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(folder / f"{st.camera_id}_{st.track_id}.jpg"), crop)

    # ------------------------------------------------------------------ small helpers
    def _emit_events(self, camera_id: str, events: List[Event]) -> None:
        if events:
            try:
                self._emit(camera_id, events)
            except Exception:
                log.exception("ANPR event emit failed")

    def _inc(self, key: str) -> None:
        with self._lock:
            self.stats[key] += 1

    def _time(self, name: str, t0: float) -> None:
        self.timers.record(name, (time.perf_counter() - t0) * 1000)
