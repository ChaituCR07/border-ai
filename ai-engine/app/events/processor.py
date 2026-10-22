import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from app.events.config import EventsConfig
from app.events.envelope import Envelope, InvalidEnvelope, parse_envelope
from app.events.streams import Fields, StreamClient, StreamUnavailable

log = logging.getLogger("events.processor")


class PermanentSinkError(Exception):
    """A sink cannot ever handle this event (retrying is pointless): send it to the dead-letter stream."""


class EventSink(ABC):
    @abstractmethod
    def handle(self, env: Envelope) -> None:
        """Process one event. MUST be idempotent: the same event can arrive more than once."""

    def close(self) -> None:
        pass


class MemorySink(EventSink):
    def __init__(self):
        self.events: List[Envelope] = []
        self._lock = threading.Lock()

    def handle(self, env):
        with self._lock:
            self.events.append(env)

    @property
    def ids(self) -> List[str]:
        with self._lock:
            return [e.event_id for e in self.events]


class JsonlFileSink(EventSink):
    """Appends each event's JSON to a file, once per event_id (a bounded memory of recent IDs)."""

    def __init__(self, path, remember: int = 50000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(self.path, "a", buffering=1, encoding="utf-8")
        self._seen: "OrderedDict[str, None]" = OrderedDict()
        self._remember = remember

    def handle(self, env):
        if env.event_id in self._seen:
            return
        self._f.write(json.dumps(env.data) + "\n")
        self._seen[env.event_id] = None
        while len(self._seen) > self._remember:
            self._seen.popitem(last=False)

    def close(self):
        self._f.close()


class ConsoleAlertSink(EventSink):
    """Prints one line per alert (a stand-in for a notification channel)."""

    def __init__(self, printer: Callable[[str], None] = print):
        self.printer = printer

    def handle(self, env):
        if env.type != "THREAT_ALERT":
            return
        d = env.data.get("details", {})
        self.printer(f"[{d.get('level', '?')}] {env.camera} | {d.get('plate', '-')} | "
                     f"score {env.data.get('threat_score', '?')} | {d.get('summary', '')}")


class EventProcessor:
    def __init__(self, client: StreamClient, sinks: List[EventSink], cfg: EventsConfig,
                 consumer: Optional[str] = None, clock: Callable[[], float] = time.time):
        self.client, self.sinks, self.cfg, self.clock = client, sinks, cfg, clock
        self.pc = cfg.processor
        self.consumer = consumer or self.pc.consumer
        self.stats: Counter = Counter()
        self._seen: "OrderedDict[str, None]" = OrderedDict()
        self._last_reclaim = 0.0
        self._stop = threading.Event()
        client.group_create(cfg.stream, self.pc.group, self.pc.start)

    # ------------------------------------------------------------------ one cycle
    def run_once(self) -> int:
        """Reclaim stale messages, read new ones, handle them. Returns how many messages were handled."""
        work: List[Tuple[str, Fields, int]] = []
        now = self.clock()
        if now - self._last_reclaim >= self.pc.reclaim_every_s:
            self._last_reclaim = now
            claimed = self.client.claim_stale(self.cfg.stream, self.pc.group, self.consumer,
                                              self.pc.reclaim_idle_ms, self.pc.batch)
            self.stats["reclaimed"] += len(claimed)
            work.extend(claimed)
        for mid, fields in self.client.read_group(self.cfg.stream, self.pc.group, self.consumer,
                                                  self.pc.batch, self.pc.block_ms):
            work.append((mid, fields, 1))
        for mid, fields, times in work:
            self._handle(mid, fields, times)
        return len(work)

    def run_forever(self) -> None:
        backoff = 0.5
        while not self._stop.is_set():
            try:
                self.run_once()
                backoff = 0.5
            except StreamUnavailable as e:
                self.stats["stream_errors"] += 1
                log.warning("Event stream unavailable (%s); retrying in %.1fs", e, backoff)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 10.0)

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ one message
    def _handle(self, mid: str, fields: Fields, times_delivered: int) -> None:
        try:
            env = parse_envelope(fields)
        except InvalidEnvelope as e:
            self._dead_letter(mid, fields, f"invalid:{e}")
            self.stats["invalid"] += 1
            return

        if env.event_id in self._seen:
            self.client.ack(self.cfg.stream, self.pc.group, [mid])
            self.stats["duplicates"] += 1
            return

        try:
            for sink in self.sinks:
                sink.handle(env)
        except PermanentSinkError as e:
            self._dead_letter(mid, fields, f"permanent:{e}")
            return
        except Exception as e:                                         # noqa: BLE001
            self.stats["sink_failures"] += 1
            if times_delivered >= self.pc.max_deliveries:
                self._dead_letter(mid, fields, f"failed_{times_delivered}_times:{type(e).__name__}:{e}")
            else:
                log.warning("Handling %s failed (attempt %d): %s; it will be retried", env.event_id,
                            times_delivered, e)
            return                                                     # left pending: redelivered later

        self.client.ack(self.cfg.stream, self.pc.group, [mid])
        self._seen[env.event_id] = None
        while len(self._seen) > self.pc.dedupe_cache:
            self._seen.popitem(last=False)
        self.stats["processed"] += 1

    def _dead_letter(self, mid: str, fields: Fields, reason: str) -> None:
        entry = {**fields, "dead_reason": reason[:500], "origin_id": mid, "group": self.pc.group,
                 "dead_at": datetime.now(timezone.utc).isoformat()}
        self.client.xadd(self.cfg.dead_stream, entry, maxlen=self.pc.dead_maxlen)
        self.client.ack(self.cfg.stream, self.pc.group, [mid])
        self.stats["dead_lettered"] += 1
        log.error("Dead-lettered message %s: %s", mid, reason)

    def status(self) -> dict:
        return dict(self.stats)
