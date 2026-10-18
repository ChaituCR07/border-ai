import logging
import queue
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, List, Optional, Tuple

import numpy as np

from app.identity.aggregate import EmbeddingAggregator
from app.identity.config import IdentityConfig
from app.identity.decision import decide_face_match
from app.identity.face import face_quality
from app.identity.gallery import ReidGallery, ReidItem
from app.pipeline.metrics import StageTimer
from app.schemas.events import REID_MATCH, WATCHLIST_MATCH, Event
from app.watchlist.cooldown import CooldownTracker
from app.watchlist.models import WatchlistHit

log = logging.getLogger("identity")


@dataclass
class _Job:
    camera_id: str
    track_id: int
    frame_id: int
    timestamp: float
    crop: np.ndarray
    do_face: bool
    do_reid: bool


@dataclass
class _State:
    camera_id: str
    track_id: int
    face: EmbeddingAggregator
    reid: EmbeddingAggregator
    first_ts: float = 0.0
    last_ts: float = 0.0
    last_frame_id: int = 0
    last_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    frames_seen: int = 0
    last_face_sched: int = -10 ** 9
    last_reid_sched: int = -10 ** 9
    face_scheduled: int = 0
    reid_scheduled: int = 0
    pending: int = 0
    face_done: bool = False
    face_searched_n: int = 0
    reid_queries: int = 0
    reid_reported: bool = False
    ended: bool = False
    flag: str = ""
    label: str = ""


def _crop(image: np.ndarray, bbox, margin: float) -> np.ndarray:
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    return image[max(0, int(y1 - my)):min(h, int(y2 + my)),
                 max(0, int(x1 - mx)):min(w, int(x2 + mx))].copy()


class IdentityService:
    def __init__(self, cfg: IdentityConfig, face_engine=None, embedder=None, face_gallery=None,
                 hit_recorder: Optional[Callable[[WatchlistHit], None]] = None):
        self.cfg = cfg
        self.face_engine = face_engine
        self.embedder = embedder
        self.face_gallery = face_gallery
        self.hit_recorder = hit_recorder
        self.reid_gallery = ReidGallery(cfg.reid.gallery_ttl_s, cfg.reid.gallery_max_items,
                                        cfg.reid.max_gap_s, cfg.reid.allow_overlap, cfg.reid.camera_pairs)
        self.cooldown = CooldownTracker(cfg.face.cooldown_s)
        self.stats: Counter = Counter()
        self.timers = StageTimer()
        self.block_when_full = False

        self._lock = threading.RLock()
        self._states: Dict[Tuple[str, int], _State] = {}
        self._q: Optional[queue.Queue] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._emit: Callable[[str, List[Event]], None] = lambda cid, events: None
        self._outbox: Deque[WatchlistHit] = deque(maxlen=1000)
        self._latest_ts = 0.0

    # ------------------------------------------------------------------ setup / lifecycle
    def attach(self, emit=None, timers: Optional[StageTimer] = None, block_when_full: bool = False):
        if emit is not None:
            self._emit = emit
        if timers is not None:
            self.timers = timers
        self.block_when_full = block_when_full
        self._q = queue.Queue(maxsize=self.cfg.queue_size)
        return self

    def start(self) -> None:
        if self.face_gallery is not None:
            self.face_gallery.reload()
        self._thread = threading.Thread(target=self._worker, name="identity-worker", daemon=True)
        self._thread.start()

    def stop(self, drain: bool = True, timeout: float = 60.0) -> None:
        deadline = time.time() + timeout
        if drain:
            if self._thread is None:
                self.run_pending()
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
            self._thread = None
        with self._lock:
            leftovers = list(self._states.values())
            self._states.clear()
        by_camera: Dict[str, List[Event]] = {}
        for st in leftovers:
            by_camera.setdefault(st.camera_id, []).extend(self._finalize_state(st))
        for cid, events in by_camera.items():
            self._emit_events(cid, events)
        self._flush_outbox()

    # ------------------------------------------------------------------ called by the pipeline
    def submit(self, camera_id: str, ft, image: np.ndarray) -> int:
        fc, rc = self.cfg.face, self.cfg.reid
        H, W = image.shape[:2]
        wanted = []
        with self._lock:
            for o in ft.tracks:
                if o.label not in self.cfg.person_classes:
                    continue
                key = (camera_id, o.track_id)
                st = self._states.get(key)
                if st is None:
                    st = _State(camera_id, o.track_id, EmbeddingAggregator(), EmbeddingAggregator(),
                                first_ts=ft.timestamp)
                    self._states[key] = st
                st.frames_seen += 1
                st.last_ts, st.last_frame_id, st.last_bbox = ft.timestamp, ft.frame_id, tuple(o.bbox)
                self._latest_ts = max(self._latest_ts, ft.timestamp)

                height = o.y2 - o.y1
                def at_border(m):
                    return bool(m) and (o.x1 < m or o.y1 < m or o.x2 > W - m or o.y2 > H - m)

                do_face = bool(
                    fc.enabled and self.face_engine is not None and not st.face_done
                    and st.face_scheduled < fc.max_reads_per_track and st.frames_seen >= fc.min_track_hits
                    and st.frames_seen - st.last_face_sched >= fc.every_n_frames
                    and height >= fc.min_person_height_px and not at_border(fc.border_margin_px))
                do_reid = bool(
                    rc.enabled and self.embedder is not None
                    and st.reid_scheduled < rc.max_samples_per_track and st.frames_seen >= rc.min_track_hits
                    and st.frames_seen - st.last_reid_sched >= rc.every_n_frames
                    and height >= rc.min_person_height_px and not at_border(rc.border_margin_px))
                if do_face or do_reid:
                    wanted.append(((o.x2 - o.x1) * height, st, do_face, do_reid, tuple(o.bbox)))

            wanted.sort(key=lambda w: -w[0])                      # biggest (closest) persons first
            jobs = []
            for _, st, do_face, do_reid, bbox in wanted[:self.cfg.max_jobs_per_frame]:
                crop = _crop(image, bbox, self.cfg.crop_margin)
                if crop.size == 0:
                    continue
                if do_face:
                    st.last_face_sched, st.face_scheduled = st.frames_seen, st.face_scheduled + 1
                if do_reid:
                    st.last_reid_sched, st.reid_scheduled = st.frames_seen, st.reid_scheduled + 1
                st.pending += 1
                jobs.append(_Job(st.camera_id, st.track_id, ft.frame_id, ft.timestamp, crop, do_face, do_reid))
            self.stats["skipped_over_cap"] += max(0, len(wanted) - len(jobs))
        for job in jobs:
            self._enqueue(job)
        return len(jobs)

    def on_tracks_removed(self, camera_id: str, tracks) -> None:
        events: List[Event] = []
        done: List[_State] = []
        with self._lock:
            for t in tracks:
                st = self._states.get((camera_id, t.track_id))
                if st is None:
                    continue
                st.ended = True
                st.last_ts = max(st.last_ts, t.last_seen)
                if st.pending <= 0:
                    self._states.pop((camera_id, t.track_id), None)
                    done.append(st)
        for st in done:
            events += self._finalize_state(st)
        self._emit_events(camera_id, events)

    def flags_snapshot(self, camera_id: str) -> Dict[int, str]:
        with self._lock:
            return {tid: st.flag for (cid, tid), st in self._states.items() if cid == camera_id and st.flag}

    def labels_snapshot(self, camera_id: str) -> Dict[int, str]:
        with self._lock:
            return {tid: st.label for (cid, tid), st in self._states.items() if cid == camera_id and st.label}

    def status(self) -> dict:
        with self._lock:
            return {"queue": self._q.qsize() if self._q is not None else 0,
                    "active_persons": len(self._states),
                    "face_gallery": len(self.face_gallery) if self.face_gallery is not None else 0,
                    "reid_gallery": len(self.reid_gallery), **dict(self.stats)}

    # ------------------------------------------------------------------ queue and worker
    def _enqueue(self, job: _Job) -> None:
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
        while True:                                               # live: drop the oldest job
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
            try:
                job = self._q.get(timeout=1.0)
            except queue.Empty:
                self._housekeeping()
                continue
            try:
                if job is None:
                    return
                self._handle(job)
            finally:
                self._q.task_done()

    def run_pending(self) -> int:
        n = 0
        while True:
            try:
                job = self._q.get_nowait()
            except queue.Empty:
                self._flush_outbox()
                return n
            try:
                if job is not None:
                    self._handle(job)
                    n += 1
            finally:
                self._q.task_done()

    def _handle(self, job: _Job) -> None:
        try:
            events = self._process(job)
        except Exception:
            log.exception("Identity job failed")
            self._inc("errors")
            events = []
        self._emit_events(job.camera_id, events)
        self._complete(job)
        self._flush_outbox()

    def _complete(self, job: _Job, dropped: bool = False) -> None:
        events: List[Event] = []
        done: Optional[_State] = None
        with self._lock:
            if dropped:
                self.stats["dropped"] += 1
            st = self._states.get((job.camera_id, job.track_id))
            if st is not None:
                st.pending -= 1
                if st.ended and st.pending <= 0:
                    self._states.pop((job.camera_id, job.track_id), None)
                    done = st
        if done is not None:
            events = self._finalize_state(done)
        self._emit_events(job.camera_id, events)

    def _housekeeping(self) -> None:
        if self.face_gallery is not None:
            self.face_gallery.maybe_reload()
        self.reid_gallery.prune(self._latest_ts)
        self._flush_outbox()

    # ------------------------------------------------------------------ the work
    def _process(self, job: _Job) -> List[Event]:
        with self._lock:
            st = self._states.get((job.camera_id, job.track_id))
        if st is None:
            return []
        events: List[Event] = []
        if job.do_face and self.face_engine is not None:
            events += self._face_step(job, st)
        if job.do_reid and self.embedder is not None:
            events += self._reid_step(job, st)
        return events

    def _face_step(self, job: _Job, st: _State) -> List[Event]:
        fc = self.cfg.face
        upper = job.crop[:max(1, int(job.crop.shape[0] * fc.upper_fraction))]

        t0 = time.perf_counter()
        faces = self.face_engine.detect(upper)
        self.timers.record("face_detect_ms", (time.perf_counter() - t0) * 1000)
        if not faces:
            self._inc("no_face")
            return []
        face = faces[0]
        quality = face_quality(upper, face, fc)
        if not quality.ok:
            self._inc(f"face_skipped_{quality.reason}")
            return []

        t1 = time.perf_counter()
        embedding = self.face_engine.embed(upper, face)
        self.timers.record("face_embed_ms", (time.perf_counter() - t1) * 1000)
        with self._lock:
            st.face.add(embedding, quality.score, job.timestamp)
            self.stats["face_embeddings"] += 1
        return self._face_decide(st, job.timestamp)

    def _face_decide(self, st: _State, ts: float) -> List[Event]:
        fc = self.cfg.face
        if self.face_gallery is None:
            return []
        with self._lock:
            n = len(st.face)
            if st.face_done or n < fc.min_embeddings or n == st.face_searched_n:
                return []
            st.face_searched_n = n
            aggregate, consistency, quality = st.face.aggregate(), st.face.consistency(), st.face.quality_mean()

        results = self.face_gallery.search(aggregate, top_k=2)
        decision = decide_face_match(results, n, consistency, fc)
        self._inc("face_searches")
        if decision.status is None:
            self._inc(f"face_no_match_{decision.reason}")
            return []

        entry = decision.entry
        allowed = self.cooldown.allow((st.camera_id, entry.watchlist_id), decision.status, ts)
        event = self._face_event(st, entry, decision, n, consistency, ts)
        self._outbox.append(WatchlistHit(
            watchlist_id=entry.watchlist_id, camera_id=st.camera_id, track_id=st.track_id, plate=None,
            match_type="face", distance=round(1.0 - decision.similarity, 4), plate_confidence=None,
            score=decision.score, status=decision.status if allowed else "suppressed",
            seen_at=datetime.fromtimestamp(ts, tz=timezone.utc),
            event_id=event.event_id if allowed else None, match_basis="face",
            similarity=decision.similarity))
        if not allowed:
            self._inc("face_suppressed")
            return []
        self._inc("face_alerts" if decision.status == "alert" else "face_reviews")
        with self._lock:
            st.face_done = True
            st.flag = entry.risk_level + (" REVIEW" if decision.status == "review" else "") + " FACE"
        return [event]

    def _face_event(self, st, entry, decision, n, consistency, ts) -> Event:
        return Event(
            type=WATCHLIST_MATCH, camera_id=st.camera_id, timestamp=ts, frame_id=st.last_frame_id,
            track_id=st.track_id, object_class="person", confidence=decision.score / 100.0,
            bbox=st.last_bbox, rule_id="FACE_WATCHLIST", rule_name="Face watchlist match",
            rule_kind="watchlist", rule_type="face",
            details={"match_basis": "face", "score": decision.score, "status": decision.status,
                     "review_required": decision.status == "review", "similarity": round(decision.similarity, 3),
                     "margin": round(decision.margin, 3), "embeddings": n,
                     "consistency": round(consistency, 3), "entry_id": entry.watchlist_id,
                     "entity_type": entry.entity_type, "risk_level": entry.risk_level,
                     "embedding_model": getattr(self.face_engine, "model_name", "unknown")})
        # Deliberately NOT included: the entry's name or description, any image, or the embedding itself.

    # ------------------------------------------------------------------ Re-ID path
    def _reid_step(self, job: _Job, st: _State) -> List[Event]:
        rc = self.cfg.reid
        t0 = time.perf_counter()
        embedding = self.embedder.embed(job.crop)
        self.timers.record("reid_embed_ms", (time.perf_counter() - t0) * 1000)
        quality = min(1.0, job.crop.shape[0] / 200.0)
        with self._lock:
            st.reid.add(embedding, quality, job.timestamp)
            self.stats["reid_embeddings"] += 1
            ready = len(st.reid) >= rc.min_samples and st.reid_queries < rc.max_queries and not st.reid_reported
        return self._reid_query(st, job.timestamp) if ready else []

    def _reid_query(self, st: _State, ts: float) -> List[Event]:
        rc = self.cfg.reid
        with self._lock:
            aggregate, n = st.reid.aggregate(), len(st.reid)
            st.reid_queries += 1
        if aggregate is None:
            return []
        candidates = [c for c in self.reid_gallery.search(aggregate, st.camera_id, st.first_ts, top_k=3)
                      if c.similarity >= rc.similarity_threshold]
        if not candidates:
            return []
        top = candidates[0]
        with self._lock:
            st.reid_reported = True
            st.label = f"= {top.camera_id} #{top.track_id}?"
        self._inc("reid_candidates")
        return [Event(
            type=REID_MATCH, camera_id=st.camera_id, timestamp=ts, frame_id=st.last_frame_id,
            track_id=st.track_id, object_class="person", confidence=top.similarity, bbox=st.last_bbox,
            rule_id="REID", rule_name="Cross-camera appearance match", rule_kind="identity", rule_type="reid",
            details={"status": "candidate", "review_required": True, "similarity": round(top.similarity, 3),
                     "samples": n, "embedder": getattr(self.embedder, "name", "unknown"),
                     "candidates": [{"camera_id": c.camera_id, "track_id": c.track_id,
                                     "similarity": round(c.similarity, 3), "gap_s": round(c.gap_s, 1)}
                                    for c in candidates]})]

    # ------------------------------------------------------------------ end of a track
    def _finalize_state(self, st: _State) -> List[Event]:
        """The track has ended and has no queued jobs. The state is no longer shared."""
        events: List[Event] = []
        rc = self.cfg.reid
        try:
            events += self._face_decide(st, st.last_ts)
            if (self.embedder is not None and len(st.reid) >= rc.min_samples
                    and not st.reid_reported and st.reid_queries < rc.max_queries):
                events += self._reid_query(st, st.last_ts)
            aggregate = st.reid.aggregate() if self.embedder is not None else None
            if aggregate is not None and len(st.reid) >= rc.min_samples:
                self.reid_gallery.add(ReidItem(st.camera_id, st.track_id, aggregate,
                                               st.first_ts, st.last_ts, len(st.reid)))
        except Exception:
            log.exception("Identity finalization failed")
            self._inc("errors")
        return events

    # ------------------------------------------------------------------ small helpers
    def _flush_outbox(self) -> None:
        while self._outbox:
            try:
                hit = self._outbox.popleft()
            except IndexError:
                return
            if self.hit_recorder is None:
                continue
            try:
                self.hit_recorder(hit)
            except Exception:
                log.exception("Could not record a face hit")

    def _emit_events(self, camera_id: str, events: List[Event]) -> None:
        if events:
            try:
                self._emit(camera_id, events)
            except Exception:
                log.exception("Identity event emit failed")

    def _inc(self, key: str) -> None:
        with self._lock:
            self.stats[key] += 1
