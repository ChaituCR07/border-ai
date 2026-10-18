import logging
import queue
import threading
import time
from collections import Counter, OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, List, Optional, Tuple

from app.pipeline.metrics import StageTimer
from app.schemas.events import PLATE_RECOGNIZED, WATCHLIST_MATCH, Event
from app.watchlist.config import WatchlistConfig
from app.watchlist.matcher import (Match, decide_status, lookup_in_repo, lookup_in_snapshot,
                                   score_for)
from app.watchlist.models import STATUS_RANK, RepoUnavailable, WatchlistHit
from app.watchlist.normalize import normalize_plate

log = logging.getLogger("watchlist")


@dataclass
class _PlateJob:
    camera_id: str
    track_id: int
    plate: str
    confidence: float
    timestamp: float
    frame_id: int
    object_class: str
    bbox: tuple
    plate_event_id: str


class WatchlistService:
    def __init__(self, repo, cfg: WatchlistConfig):
        self.repo = repo
        self.cfg = cfg
        self.stats: Counter = Counter()
        self.timers = StageTimer()
        self.block_when_full = False

        self._lock = threading.RLock()
        self._q: Optional[queue.Queue] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._emit: Callable[[str, List[Event]], None] = lambda cid, events: None

        self._snapshot: list = []
        self._snapshot_at = 0.0
        self._db_ok = True
        self._unsaved: Deque[WatchlistHit] = deque(maxlen=1000)
        self._seen: "OrderedDict[Tuple[str, int], set]" = OrderedDict()      # (camera, track) -> plates looked up
        self._last: Dict[Tuple[str, int], Tuple[float, str]] = {}            # (camera, entry) -> (time, status)
        self._flags: Dict[Tuple[str, int], str] = {}                         # (camera, track) -> label

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
        self.refresh_snapshot()
        self._thread = threading.Thread(target=self._worker, name="watchlist-worker", daemon=True)
        self._thread.start()

    def stop(self, drain: bool = True, timeout: float = 30.0) -> None:
        deadline = time.time() + timeout
        if drain:
            if self._thread is None:
                self.run_pending()
            else:
                while self._q.unfinished_tasks and time.time() < deadline:
                    time.sleep(0.02)
        self._stop.set()
        if self._thread is not None:
            try:
                self._q.put(None, timeout=2)
            except queue.Full:
                pass
            self._thread.join(timeout=5)
            self._thread = None
        self.run_housekeeping(force=True)                      # last attempt to save queued hits

    # ------------------------------------------------------------------ called by the pipeline
    def submit(self, event: Event) -> bool:
        """Queue a PLATE_RECOGNIZED event for lookup. Returns False if it was ignored or dropped."""
        if event.type != PLATE_RECOGNIZED:
            return False
        plate = event.details.get("plate")
        if not plate:
            return False
        job = _PlateJob(event.camera_id, event.track_id, plate, float(event.confidence), event.timestamp,
                        event.frame_id, event.object_class, tuple(event.bbox), event.event_id)
        try:
            self._q.put(job, timeout=None if self.block_when_full else self.cfg.submit_timeout_s)
        except queue.Full:
            self._inc("dropped")
            log.error("Watchlist queue full: lookup for %s on %s dropped", plate, event.camera_id)
            return False
        self._inc("queued")
        return True

    def on_tracks_removed(self, camera_id: str, tracks) -> None:
        with self._lock:
            for t in tracks:
                self._flags.pop((camera_id, t.track_id), None)
                self._seen.pop((camera_id, t.track_id), None)

    def flags_snapshot(self, camera_id: str) -> Dict[int, str]:
        with self._lock:
            return {tid: label for (cid, tid), label in self._flags.items() if cid == camera_id}

    def status(self) -> dict:
        with self._lock:
            return {"queue": self._q.qsize() if self._q is not None else 0,
                    "db_ok": self._db_ok, "snapshot_size": len(self._snapshot),
                    "hits_unsaved": len(self._unsaved), "flagged_tracks": len(self._flags),
                    **dict(self.stats)}

    # ------------------------------------------------------------------ worker
    def _worker(self) -> None:
        while True:
            try:
                job = self._q.get(timeout=1.0)
            except queue.Empty:
                self.run_housekeeping()
                continue
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

    def _handle(self, job: _PlateJob) -> None:
        t0 = time.perf_counter()
        try:
            events = self._process(job)
        except Exception:
            log.exception("Watchlist job failed")
            self._inc("errors")
            events = []
        self.timers.record("watchlist_ms", (time.perf_counter() - t0) * 1000)
        if events:
            try:
                self._emit(job.camera_id, events)
            except Exception:
                log.exception("Watchlist event emit failed")

    # ------------------------------------------------------------------ the lookup itself
    def _process(self, job: _PlateJob) -> List[Event]:
        cfg = self.cfg
        plate = normalize_plate(job.plate)
        key = (job.camera_id, job.track_id)

        with self._lock:
            seen = self._seen.setdefault(key, set())
            self._seen.move_to_end(key)
            while len(self._seen) > 2000:
                self._seen.popitem(last=False)
            if plate in seen:
                self.stats["skipped_repeat"] += 1
                return []
            seen.add(plate)

        match = self._lookup(plate)
        if match is None:
            self._inc("no_match")
            return []

        score = score_for(job.confidence, match.quality)
        status = decide_status(match, job.confidence, score, cfg)
        if status is None:
            self._inc("below_min_score")
            return []

        entry = match.entry
        event = self._build_event(job, match, score, status)

        stored = status
        with self._lock:
            last = self._last.get((job.camera_id, entry.watchlist_id))
            if (last is not None and (job.timestamp - last[0]) < cfg.cooldown_s
                    and STATUS_RANK[status] <= STATUS_RANK[last[1]]):
                stored = "suppressed"
            else:
                self._last[(job.camera_id, entry.watchlist_id)] = (job.timestamp, status)

        self._persist(WatchlistHit(
            watchlist_id=entry.watchlist_id, camera_id=job.camera_id, track_id=job.track_id,
            plate=plate, match_type=match.match_type, distance=match.distance,
            plate_confidence=job.confidence, score=score, status=stored,
            event_id=None if stored == "suppressed" else event.event_id,
            seen_at=datetime.fromtimestamp(job.timestamp, tz=timezone.utc)))

        if stored == "suppressed":
            self._inc("suppressed")
            return []

        self._inc("alerts" if status == "alert" else "reviews")
        with self._lock:
            self._flags[key] = entry.risk_level + (" REVIEW" if status == "review" else "")
        return [event]

    def _lookup(self, plate: str) -> Optional[Match]:
        try:
            match = lookup_in_repo(self.repo, plate, self.cfg)
            with self._lock:
                self._db_ok = True
            return match
        except RepoUnavailable as e:
            with self._lock:
                if self._db_ok:
                    log.error("Watchlist database unreachable (%s); using the in-memory snapshot", e)
                self._db_ok = False
                snapshot = list(self._snapshot)
                self.stats["fallback_lookups"] += 1
            return lookup_in_snapshot(snapshot, plate, self.cfg)

    def _build_event(self, job: _PlateJob, match: Match, score: int, status: str) -> Event:
        e = match.entry
        return Event(
            type=WATCHLIST_MATCH, camera_id=job.camera_id, timestamp=job.timestamp,
            frame_id=job.frame_id, track_id=job.track_id, object_class=job.object_class,
            confidence=score / 100.0, bbox=job.bbox, rule_id="WATCHLIST",
            rule_name="Watchlist match", rule_kind="watchlist", rule_type=e.entity_type.lower(),
            details={"plate": job.plate, "score": score, "status": status,
                     "review_required": status == "review", "entry_id": e.watchlist_id,
                     "entity_type": e.entity_type, "risk_level": e.risk_level,
                     "match_type": match.match_type, "distance": round(match.distance, 2),
                     "matched_identifier": e.normalized_identifier,
                     "plate_confidence": round(job.confidence, 3), "also_matched": match.also,
                     "plate_event_id": job.plate_event_id})
        # Deliberately NOT included: the entry's name and description (see decision 10).

    # ------------------------------------------------------------------ persistence and housekeeping
    def persist_hit(self, hit: WatchlistHit) -> None:
        """Save a hit; if the database is down, queue it for retry (shared by the identity service)."""
        self._persist(hit)

    def _persist(self, hit: WatchlistHit) -> None:
        try:
            self.repo.record_hit(hit)
        except RepoUnavailable:
            with self._lock:
                self._unsaved.append(hit)
                self.stats["hits_unsaved_total"] += 1

    def refresh_snapshot(self) -> bool:
        try:
            entries = self.repo.load_active(self.cfg.entity_types)
        except RepoUnavailable:
            self._inc("snapshot_errors")
            return False
        with self._lock:
            self._snapshot = entries
            self._snapshot_at = time.time()
        return True

    def run_housekeeping(self, force: bool = False) -> None:
        """Refresh the snapshot when due and retry hits that could not be saved."""
        if force or time.time() - self._snapshot_at >= self.cfg.snapshot_refresh_s:
            self.refresh_snapshot()
        while True:
            with self._lock:
                hit = self._unsaved.popleft() if self._unsaved else None
            if hit is None:
                return
            try:
                self.repo.record_hit(hit)
            except RepoUnavailable:
                with self._lock:
                    self._unsaved.appendleft(hit)
                return

    def _inc(self, key: str) -> None:
        with self._lock:
            self.stats[key] += 1
