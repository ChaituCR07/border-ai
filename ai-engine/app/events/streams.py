import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple

Fields = Dict[str, str]


class StreamUnavailable(Exception):
    """The stream backend cannot be reached or refused the request."""


class StreamClient(ABC):
    @abstractmethod
    def xadd(self, stream: str, fields: Fields, maxlen: Optional[int] = None, approximate: bool = True) -> str: ...

    def xadd_many(self, stream: str, items: List[Fields], maxlen: Optional[int] = None,
                  approximate: bool = True) -> List[str]:
        return [self.xadd(stream, f, maxlen, approximate) for f in items]

    @abstractmethod
    def group_create(self, stream: str, group: str, start: str = "0") -> None:
        """Create the stream and the consumer group if they do not exist (idempotent)."""

    @abstractmethod
    def read_group(self, stream: str, group: str, consumer: str, count: int = 10,
                   block_ms: int = 0) -> List[Tuple[str, Fields]]:
        """New messages for this group, each delivered to one consumer. Returns [] when there are none."""

    @abstractmethod
    def ack(self, stream: str, group: str, ids: List[str]) -> None: ...

    @abstractmethod
    def claim_stale(self, stream: str, group: str, consumer: str, min_idle_ms: int,
                    count: int = 10) -> List[Tuple[str, Fields, int]]:
        """Take over messages pending for at least min_idle_ms. Returns (id, fields, times_delivered)."""

    @abstractmethod
    def length(self, stream: str) -> int: ...

    @abstractmethod
    def pending_count(self, stream: str, group: str) -> int: ...

    @abstractmethod
    def groups_info(self, stream: str) -> List[dict]: ...

    @abstractmethod
    def range(self, stream: str, count: int = 10) -> List[Tuple[str, Fields]]:
        """The newest `count` entries, oldest first."""

    @abstractmethod
    def delete(self, stream: str) -> None: ...


def _parse_id(mid: str) -> Tuple[int, int]:
    ms, _, seq = mid.partition("-")
    return int(ms), int(seq or 0)


# ----------------------------------------------------------------------------- in-memory
class InMemoryStreamClient(StreamClient):
    """A faithful small model of Redis Streams with consumer groups, for tests and dry runs.
    `down = True` simulates an outage; `fail_after_adds = n` fails once after n successful adds."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._cond = threading.Condition()
        self._streams: Dict[str, List[Tuple[Tuple[int, int], str, Fields]]] = {}
        self._groups: Dict[Tuple[str, str], dict] = {}
        self._last_ms, self._seq = 0, 0
        self.down = False
        self.fail_after_adds: Optional[int] = None

    def _check(self) -> None:
        if self.down:
            raise StreamUnavailable("simulated outage")

    def _next_id(self) -> Tuple[int, int]:
        ms = max(int(self._clock() * 1000), self._last_ms)
        self._seq = self._seq + 1 if ms == self._last_ms else 0
        self._last_ms = ms
        return ms, self._seq

    def xadd(self, stream, fields, maxlen=None, approximate=True):
        with self._cond:
            self._check()
            if self.fail_after_adds is not None:
                if self.fail_after_adds <= 0:
                    self.fail_after_adds = None
                    raise StreamUnavailable("simulated failure in the middle of a batch")
                self.fail_after_adds -= 1
            tup = self._next_id()
            mid = f"{tup[0]}-{tup[1]}"
            entries = self._streams.setdefault(stream, [])
            entries.append((tup, mid, {str(k): str(v) for k, v in fields.items()}))
            if maxlen is not None and not approximate:
                del entries[:max(0, len(entries) - maxlen)]
            elif maxlen is not None and len(entries) > maxlen * 2:        # approximate: trim lazily
                del entries[:len(entries) - maxlen]
            self._cond.notify_all()
            return mid

    def group_create(self, stream, group, start="0"):
        with self._cond:
            self._check()
            entries = self._streams.setdefault(stream, [])
            if (stream, group) not in self._groups:
                last = (0, 0) if start == "0" or not entries else entries[-1][0]
                self._groups[(stream, group)] = {"last": last, "pending": {}, "consumers": set()}

    def _group(self, stream, group):
        if (stream, group) not in self._groups:
            raise StreamUnavailable(f"NOGROUP no such consumer group {group!r} for {stream!r}")
        return self._groups[(stream, group)]

    def _collect(self, stream, g, consumer, count):
        out, now = [], int(self._clock() * 1000)
        for tup, mid, fields in self._streams.get(stream, []):
            if tup > g["last"]:
                g["pending"][mid] = [consumer, now, 1]
                g["last"] = tup
                out.append((mid, dict(fields)))
                if len(out) >= count:
                    break
        g["consumers"].add(consumer)
        return out

    def read_group(self, stream, group, consumer, count=10, block_ms=0):
        with self._cond:
            self._check()
            g = self._group(stream, group)
            msgs = self._collect(stream, g, consumer, count)
            if not msgs and block_ms > 0:
                self._cond.wait(timeout=block_ms / 1000.0)
                self._check()
                msgs = self._collect(stream, g, consumer, count)
            return msgs

    def ack(self, stream, group, ids):
        with self._cond:
            self._check()
            g = self._group(stream, group)
            for mid in ids:
                g["pending"].pop(mid, None)

    def claim_stale(self, stream, group, consumer, min_idle_ms, count=10):
        with self._cond:
            self._check()
            g, now, out = self._group(stream, group), int(self._clock() * 1000), []
            by_id = {mid: fields for _, mid, fields in self._streams.get(stream, [])}
            for mid in sorted(g["pending"], key=_parse_id):
                owner, delivered, times = g["pending"][mid]
                if now - delivered < min_idle_ms:
                    continue
                if mid not in by_id:                                  # trimmed away: nothing left to deliver
                    del g["pending"][mid]
                    continue
                g["pending"][mid] = [consumer, now, times + 1]
                g["consumers"].add(consumer)
                out.append((mid, dict(by_id[mid]), times + 1))
                if len(out) >= count:
                    break
            return out

    def length(self, stream):
        with self._cond:
            self._check()
            return len(self._streams.get(stream, []))

    def pending_count(self, stream, group):
        with self._cond:
            self._check()
            return len(self._group(stream, group)["pending"])

    def groups_info(self, stream):
        with self._cond:
            self._check()
            entries = self._streams.get(stream, [])
            return [{"name": grp, "consumers": len(g["consumers"]), "pending": len(g["pending"]),
                     "last-delivered-id": f"{g['last'][0]}-{g['last'][1]}",
                     "lag": sum(1 for t, _, _ in entries if t > g["last"])}
                    for (st, grp), g in self._groups.items() if st == stream]

    def range(self, stream, count=10):
        with self._cond:
            self._check()
            return [(mid, dict(f)) for _, mid, f in self._streams.get(stream, [])[-count:]]

    def delete(self, stream):
        with self._cond:
            self._streams.pop(stream, None)
            for key in [k for k in self._groups if k[0] == stream]:
                del self._groups[key]


# ----------------------------------------------------------------------------- Redis
class RedisStreamClient(StreamClient):
    """Redis Streams through redis-py (decode_responses=True)."""

    def __init__(self, client):
        import redis
        self.r = client
        self._errors = redis.exceptions.RedisError

    @classmethod
    def from_url(cls, url: str) -> "RedisStreamClient":
        import redis
        return cls(redis.Redis.from_url(url, decode_responses=True, socket_timeout=5, socket_connect_timeout=3))

    def _guard(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except self._errors as e:
            raise StreamUnavailable(str(e)) from e

    def xadd(self, stream, fields, maxlen=None, approximate=True):
        if maxlen:
            return self._guard(self.r.xadd, stream, fields, maxlen=maxlen, approximate=approximate)
        return self._guard(self.r.xadd, stream, fields)

    def xadd_many(self, stream, items, maxlen=None, approximate=True):
        def run():
            pipe = self.r.pipeline(transaction=False)
            for fields in items:
                if maxlen:
                    pipe.xadd(stream, fields, maxlen=maxlen, approximate=approximate)
                else:
                    pipe.xadd(stream, fields)
            return pipe.execute()
        return self._guard(run)

    def group_create(self, stream, group, start="0"):
        try:
            self.r.xgroup_create(stream, group, id=start, mkstream=True)
        except self._errors as e:
            if "BUSYGROUP" not in str(e):
                raise StreamUnavailable(str(e)) from e

    def read_group(self, stream, group, consumer, count=10, block_ms=0):
        result = self._guard(self.r.xreadgroup, group, consumer, {stream: ">"}, count=count,
                             block=block_ms or None)
        return [(mid, fields) for _, entries in (result or []) for mid, fields in entries]

    def ack(self, stream, group, ids):
        if ids:
            self._guard(self.r.xack, stream, group, *ids)

    def claim_stale(self, stream, group, consumer, min_idle_ms, count=10):
        result = self._guard(self.r.xautoclaim, stream, group, consumer, min_idle_time=min_idle_ms,
                             start_id="0-0", count=count)
        messages = result[1] if len(result) > 1 else []
        out = []
        for mid, fields in messages:
            if fields is None:                                            # deleted or trimmed entry
                continue
            info = self._guard(self.r.xpending_range, stream, group, min=mid, max=mid, count=1)
            out.append((mid, fields, int(info[0]["times_delivered"]) if info else 1))
        return out

    def length(self, stream):
        return int(self._guard(self.r.xlen, stream))

    def pending_count(self, stream, group):
        return int(self._guard(self.r.xpending, stream, group)["pending"])

    def groups_info(self, stream):
        return self._guard(self.r.xinfo_groups, stream)

    def range(self, stream, count=10):
        return list(reversed(self._guard(self.r.xrevrange, stream, count=count)))

    def delete(self, stream):
        self._guard(self.r.delete, stream)
