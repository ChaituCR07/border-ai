import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import Counter, deque
from typing import Deque, List, Tuple

from app.events.config import EventsConfig
from app.events.envelope import Envelope, envelope_from_event
from app.events.streams import StreamClient, StreamUnavailable
from app.schemas.events import Event

log = logging.getLogger("events.publisher")


class TransportUnavailable(Exception):
    """The bus cannot take events right now; the publisher will retry."""


class Transport(ABC):
    @abstractmethod
    def send(self, batch: List[Envelope]) -> None:
        """Deliver the batch or raise TransportUnavailable. May have delivered part of it before failing."""

    def close(self) -> None:
        pass


class StreamTransport(Transport):
    """Writes envelopes to the main stream, and alert types also to the alerts stream."""

    def __init__(self, client: StreamClient, cfg: EventsConfig):
        self.client, self.cfg = client, cfg

    def send(self, batch: List[Envelope]) -> None:
        try:
            self.client.xadd_many(self.cfg.stream, [e.to_fields() for e in batch], maxlen=self.cfg.maxlen)
            alerts = [e.to_fields() for e in batch if e.type in self.cfg.alert_types]
            if alerts:
                self.client.xadd_many(self.cfg.alerts_stream, alerts, maxlen=self.cfg.alerts_maxlen)
        except StreamUnavailable as e:
            raise TransportUnavailable(str(e)) from e


class EventPublisher:
    def __init__(self, transport: Transport, cfg: EventsConfig, run_id: str = ""):
        self.transport, self.cfg, self.run_id = transport, cfg, run_id
        self._high_types = set(cfg.high_priority_types)
        self._cond = threading.Condition()
        self._high: Deque[Tuple[int, Event]] = deque()
        self._low: Deque[Tuple[int, Event]] = deque()
        self._seq = 0
        self._thread = None
        self._stopping = False
        self._deadline = 0.0
        self.stats: Counter = Counter()
        self.connected = True
        self.last_error = ""
        self._last_drop_log = 0.0

    # ------------------------------------------------------------------ called by the pipeline
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="event-publisher", daemon=True)
        self._thread.start()

    def publish(self, event: Event) -> bool:
        """Queue an event. Returns immediately, never raises, never waits for the network."""
        try:
            high = event.type in self._high_types
            queue, cap = (self._high, self.cfg.buffer_high) if high else (self._low, self.cfg.buffer_low)
            dropped = 0
            with self._cond:
                self._seq += 1
                queue.append((self._seq, event))
                while len(queue) > cap:
                    queue.popleft()
                    dropped += 1
                self.stats["accepted"] += 1
                self.stats["dropped_high" if high else "dropped_low"] += dropped
                self._cond.notify()
            if dropped:
                self._log_drop(high, dropped)
            return True
        except Exception:                                      # noqa: BLE001  (publishing must never break the pipeline)
            self.stats["publish_errors"] += 1
            return False

    def stop(self, drain: bool = True, timeout: float = 10.0) -> None:
        with self._cond:
            self._stopping = True
            self._deadline = time.time() + (timeout if drain else 0.0)
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout + 2.0)
        self.transport.close()

    def status(self) -> dict:
        with self._cond:
            return {"connected": self.connected, "queued_high": len(self._high), "queued_low": len(self._low),
                    "last_error": self.last_error, **dict(self.stats)}

    # ------------------------------------------------------------------ the publisher thread
    def _log_drop(self, high: bool, n: int) -> None:
        now = time.time()
        if now - self._last_drop_log > 5.0:                    # rate-limited: an outage can drop thousands
            self._last_drop_log = now
            log.error("Event buffer full while the bus is unavailable: dropped %d %s event(s); "
                      "they remain in the journal", n, "precious" if high else "noisy")

    def _take_batch(self) -> List[Tuple[int, Event]]:
        with self._cond:
            if not (self._high or self._low) and not self._stopping:
                self._cond.wait(timeout=self.cfg.flush_ms / 1000.0)
            batch: List[Tuple[int, Event]] = []
            while len(batch) < self.cfg.batch_size and (self._high or self._low):
                take_high = self._high and (not self._low or self._high[0][0] < self._low[0][0])
                batch.append((self._high if take_high else self._low).popleft())
            return batch

    def _requeue(self, batch: List[Tuple[int, Event]]) -> None:
        with self._cond:
            for item in reversed(batch):
                (self._high if item[1].type in self._high_types else self._low).appendleft(item)
            for queue, cap, key in ((self._high, self.cfg.buffer_high, "dropped_high"),
                                    (self._low, self.cfg.buffer_low, "dropped_low")):
                while len(queue) > cap:
                    queue.popleft()
                    self.stats[key] += 1

    def _pending(self) -> int:
        with self._cond:
            return len(self._high) + len(self._low)

    def _run(self) -> None:
        backoff = self.cfg.retry_initial_s
        while True:
            batch = self._take_batch()
            if not batch:
                with self._cond:
                    if self._stopping:
                        return
                continue

            envelopes = []
            for _, event in batch:
                try:
                    envelopes.append(envelope_from_event(event, self.run_id))
                except Exception:                              # noqa: BLE001
                    self.stats["invalid_events"] += 1
                    log.exception("Could not build an envelope for %s; skipping it", getattr(event, "type", "?"))
            if not envelopes:
                continue

            try:
                self.transport.send(envelopes)
            except TransportUnavailable as e:
                self._requeue(batch)
                self.connected, self.last_error = False, str(e)
                self.stats["retries"] += 1
                if backoff == self.cfg.retry_initial_s:
                    log.warning("Event bus unavailable (%s); buffering events and retrying", e)
                if self._stopping and time.time() >= self._deadline:
                    self.stats["dropped_on_shutdown"] += self._clear()
                    return
                time.sleep(min(backoff, max(0.0, self._deadline - time.time()) if self._stopping else backoff))
                backoff = min(backoff * 2, self.cfg.retry_max_s)
                continue

            if not self.connected:
                log.info("Event bus reachable again")
            self.connected, self.last_error, backoff = True, "", self.cfg.retry_initial_s
            self.stats["published"] += len(envelopes)
            if self._stopping and time.time() >= self._deadline and self._pending():
                self.stats["dropped_on_shutdown"] += self._clear()
                return

    def _clear(self) -> int:
        with self._cond:
            n = len(self._high) + len(self._low)
            self._high.clear()
            self._low.clear()
            return n
