import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from app.watchlist.models import (
    DuplicateEntry,
    EntryNotFound,
    RepoUnavailable,
    WatchlistEntry,
    WatchlistHit,
)
from app.watchlist.normalize import prepare_entry, validate_update_fields


class WatchlistRepo(ABC):
    # ---- management
    @abstractmethod
    def add(self, entity_type, identifier, name, risk_level, description="", actor="system") -> WatchlistEntry: ...

    @abstractmethod
    def get(self, watchlist_id: int) -> WatchlistEntry: ...

    @abstractmethod
    def list_entries(self, entity_types: Optional[Sequence[str]] = None, active_only: bool = True,
                     limit: int = 1000) -> List[WatchlistEntry]: ...

    @abstractmethod
    def update(self, watchlist_id: int, actor: str = "system", **fields) -> WatchlistEntry: ...

    @abstractmethod
    def deactivate(self, watchlist_id: int, actor: str = "system", reason: str = "") -> WatchlistEntry: ...

    @abstractmethod
    def restore(self, watchlist_id: int, actor: str = "system") -> WatchlistEntry: ...

    # ---- lookup (active entries only)
    @abstractmethod
    def find_exact(self, normalized: str, entity_types: Sequence[str]) -> List[WatchlistEntry]: ...

    @abstractmethod
    def find_same_length(self, normalized: str, entity_types: Sequence[str],
                         limit: int = 5000) -> List[WatchlistEntry]: ...

    @abstractmethod
    def load_active(self, entity_types: Sequence[str]) -> List[WatchlistEntry]: ...

    # ---- history
    @abstractmethod
    def record_hit(self, hit: WatchlistHit) -> int: ...

    @abstractmethod
    def recent_hits(self, limit: int = 50, watchlist_id: Optional[int] = None) -> List[dict]: ...

    @abstractmethod
    def audit_log(self, limit: int = 100) -> List[dict]: ...

    @abstractmethod
    def ping(self) -> None:
        """Raises RepoUnavailable when the store cannot be reached."""

    def close(self) -> None:
        pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryWatchlistRepo(WatchlistRepo):
    """Thread-safe, dictionary-backed repository. `fail = True` simulates an outage."""

    def __init__(self):
        self._lock = threading.RLock()
        self._entries: Dict[int, WatchlistEntry] = {}
        self._hits: List[dict] = []
        self._audit: List[dict] = []
        self._next_id, self._next_hit, self._next_audit = 1, 1, 1
        self.fail = False

    def _check(self) -> None:
        if self.fail:
            raise RepoUnavailable("simulated outage")

    def _log(self, watchlist_id, action, actor, details=None) -> None:
        self._audit.append({"audit_id": self._next_audit, "watchlist_id": watchlist_id,
                            "action": action, "actor": actor, "details": details or {},
                            "created_at": _now()})
        self._next_audit += 1

    def _conflict(self, entry: WatchlistEntry, ignore_id: Optional[int] = None) -> bool:
        return any(e.active and e.watchlist_id != ignore_id and e.entity_type == entry.entity_type
                   and e.normalized_identifier == entry.normalized_identifier
                   for e in self._entries.values())

    def add(self, entity_type, identifier, name, risk_level, description="", actor="system"):
        self._check()
        p = prepare_entry(entity_type, identifier, name, risk_level, description)
        with self._lock:
            now = _now()
            entry = WatchlistEntry(self._next_id, p.entity_type, p.identifier, p.normalized, p.name,
                                   p.description, p.risk_level, True, actor, now, now)
            if self._conflict(entry):
                raise DuplicateEntry(f"{p.entity_type} {p.normalized} is already on the watchlist")
            self._entries[entry.watchlist_id] = entry
            self._next_id += 1
            self._log(entry.watchlist_id, "ADD", actor,
                      {"entity_type": p.entity_type, "risk_level": p.risk_level})
            return replace(entry)

    def get(self, watchlist_id):
        self._check()
        with self._lock:
            if watchlist_id not in self._entries:
                raise EntryNotFound(f"no watchlist entry {watchlist_id}")
            return replace(self._entries[watchlist_id])

    def list_entries(self, entity_types=None, active_only=True, limit=1000):
        self._check()
        with self._lock:
            items = [e for e in self._entries.values()
                     if (e.active or not active_only) and (not entity_types or e.entity_type in entity_types)]
        return [replace(e) for e in sorted(items, key=lambda e: e.watchlist_id)[:limit]]

    def update(self, watchlist_id, actor="system", **fields):
        self._check()
        changes = validate_update_fields(fields)
        with self._lock:
            if watchlist_id not in self._entries:
                raise EntryNotFound(f"no watchlist entry {watchlist_id}")
            if changes:
                self._entries[watchlist_id] = replace(self._entries[watchlist_id],
                                                      updated_at=_now(), **changes)
                self._log(watchlist_id, "UPDATE", actor, {"changed": sorted(changes)})
            return replace(self._entries[watchlist_id])

    def deactivate(self, watchlist_id, actor="system", reason=""):
        self._check()
        with self._lock:
            if watchlist_id not in self._entries:
                raise EntryNotFound(f"no watchlist entry {watchlist_id}")
            entry = self._entries[watchlist_id]
            if entry.active:
                entry = replace(entry, active=False, updated_at=_now())
                self._entries[watchlist_id] = entry
                self._log(watchlist_id, "DEACTIVATE", actor, {"reason": reason})
            return replace(entry)

    def restore(self, watchlist_id, actor="system"):
        self._check()
        with self._lock:
            if watchlist_id not in self._entries:
                raise EntryNotFound(f"no watchlist entry {watchlist_id}")
            entry = self._entries[watchlist_id]
            if not entry.active:
                if self._conflict(entry, ignore_id=watchlist_id):
                    raise DuplicateEntry("another active entry already uses this identifier")
                entry = replace(entry, active=True, updated_at=_now())
                self._entries[watchlist_id] = entry
                self._log(watchlist_id, "RESTORE", actor)
            return replace(entry)

    def find_exact(self, normalized, entity_types):
        self._check()
        with self._lock:
            return [replace(e) for e in sorted(self._entries.values(), key=lambda e: e.watchlist_id)
                    if e.active and e.entity_type in entity_types and e.normalized_identifier == normalized]

    def find_same_length(self, normalized, entity_types, limit=5000):
        self._check()
        with self._lock:
            items = [e for e in sorted(self._entries.values(), key=lambda e: e.watchlist_id)
                     if e.active and e.entity_type in entity_types
                     and len(e.normalized_identifier) == len(normalized)]
        return [replace(e) for e in items[:limit]]

    def load_active(self, entity_types):
        self._check()
        with self._lock:
            return [replace(e) for e in sorted(self._entries.values(), key=lambda e: e.watchlist_id)
                    if e.active and e.entity_type in entity_types]

    def record_hit(self, hit):
        self._check()
        with self._lock:
            if hit.watchlist_id not in self._entries:
                raise EntryNotFound(f"no watchlist entry {hit.watchlist_id}")
            row = {"hit_id": self._next_hit, "watchlist_id": hit.watchlist_id, "camera_id": hit.camera_id,
                   "track_id": hit.track_id, "plate": hit.plate, "match_type": hit.match_type,
                   "distance": hit.distance, "plate_confidence": hit.plate_confidence,
                   "score": hit.score, "status": hit.status, "event_id": hit.event_id,
                   "seen_at": hit.seen_at}
            self._hits.append(row)
            self._next_hit += 1
            return row["hit_id"]

    def recent_hits(self, limit=50, watchlist_id=None):
        self._check()
        with self._lock:
            rows = [dict(r) for r in self._hits if watchlist_id is None or r["watchlist_id"] == watchlist_id]
        return list(reversed(rows))[:limit]

    def audit_log(self, limit=100):
        self._check()
        with self._lock:
            return [dict(r) for r in reversed(self._audit)][:limit]

    def ping(self):
        self._check()


# ----------------------------------------------------------------------------- PostgreSQL

import psycopg  # noqa: E402
from psycopg.errors import ForeignKeyViolation, UniqueViolation  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg.types.json import Jsonb  # noqa: E402
from psycopg_pool import ConnectionPool, PoolTimeout  # noqa: E402

COLS = ("watchlist_id, entity_type, identifier, normalized_identifier, name, description, "
        "risk_level, active, created_by, created_at, updated_at")
HIT_COLS = ("hit_id, watchlist_id, camera_id, track_id, plate, match_type, distance, "
            "plate_confidence, score, status, event_id, seen_at")


class PostgresWatchlistRepo(WatchlistRepo):
    """PostgreSQL-backed repository. Every query is parameterized."""

    def __init__(self, dsn: str, max_size: int = 4, timeout: float = 3.0):
        self.timeout = timeout
        self.pool = ConnectionPool(dsn, min_size=1, max_size=max_size,
                                   kwargs={"row_factory": dict_row}, open=False)
        self.pool.open(wait=False)             # never blocks startup; unreachable -> RepoUnavailable later

    @contextmanager
    def _conn(self):
        try:
            with self.pool.connection(timeout=self.timeout) as conn:
                yield conn
        except (psycopg.OperationalError, PoolTimeout) as e:
            raise RepoUnavailable(str(e)) from e

    @staticmethod
    def _audit(conn, watchlist_id, action, actor, details=None) -> None:
        conn.execute("INSERT INTO watchlist_audit (watchlist_id, action, actor, details) "
                     "VALUES (%s, %s, %s, %s)", (watchlist_id, action, actor, Jsonb(details or {})))

    def add(self, entity_type, identifier, name, risk_level, description="", actor="system"):
        p = prepare_entry(entity_type, identifier, name, risk_level, description)
        with self._conn() as conn:
            try:
                row = conn.execute(
                    "INSERT INTO watchlist (entity_type, identifier, normalized_identifier, name, "
                    "description, risk_level, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    f"RETURNING {COLS}",
                    (p.entity_type, p.identifier, p.normalized, p.name, p.description,
                     p.risk_level, actor)).fetchone()
            except UniqueViolation:
                raise DuplicateEntry(f"{p.entity_type} {p.normalized} is already on the watchlist") from None
            self._audit(conn, row["watchlist_id"], "ADD", actor,
                        {"entity_type": p.entity_type, "risk_level": p.risk_level})
        return WatchlistEntry(**row)

    def get(self, watchlist_id):
        with self._conn() as conn:
            row = conn.execute(f"SELECT {COLS} FROM watchlist WHERE watchlist_id = %s",
                               (watchlist_id,)).fetchone()
        if row is None:
            raise EntryNotFound(f"no watchlist entry {watchlist_id}")
        return WatchlistEntry(**row)

    def list_entries(self, entity_types=None, active_only=True, limit=1000):
        clauses, params = [], []
        if active_only:
            clauses.append("active")
        if entity_types:
            clauses.append("entity_type = ANY(%s)")
            params.append(list(entity_types))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM watchlist {where} ORDER BY watchlist_id LIMIT %s",
                                (*params, limit)).fetchall()
        return [WatchlistEntry(**r) for r in rows]

    def update(self, watchlist_id, actor="system", **fields):
        changes = validate_update_fields(fields)
        if not changes:
            return self.get(watchlist_id)
        sets = ", ".join(f"{col} = %s" for col in changes)        # column names come from the whitelist
        with self._conn() as conn:
            row = conn.execute(f"UPDATE watchlist SET {sets}, updated_at = now() "
                               f"WHERE watchlist_id = %s RETURNING {COLS}",
                               (*changes.values(), watchlist_id)).fetchone()
            if row is None:
                raise EntryNotFound(f"no watchlist entry {watchlist_id}")
            self._audit(conn, watchlist_id, "UPDATE", actor, {"changed": sorted(changes)})
        return WatchlistEntry(**row)

    def deactivate(self, watchlist_id, actor="system", reason=""):
        with self._conn() as conn:
            row = conn.execute("UPDATE watchlist SET active = FALSE, updated_at = now() "
                               f"WHERE watchlist_id = %s AND active RETURNING {COLS}",
                               (watchlist_id,)).fetchone()
            if row is None:
                existing = conn.execute(f"SELECT {COLS} FROM watchlist WHERE watchlist_id = %s",
                                        (watchlist_id,)).fetchone()
                if existing is None:
                    raise EntryNotFound(f"no watchlist entry {watchlist_id}")
                return WatchlistEntry(**existing)                  # already inactive: idempotent
            self._audit(conn, watchlist_id, "DEACTIVATE", actor, {"reason": reason})
        return WatchlistEntry(**row)

    def restore(self, watchlist_id, actor="system"):
        with self._conn() as conn:
            try:
                row = conn.execute("UPDATE watchlist SET active = TRUE, updated_at = now() "
                                   f"WHERE watchlist_id = %s AND NOT active RETURNING {COLS}",
                                   (watchlist_id,)).fetchone()
            except UniqueViolation:
                raise DuplicateEntry("another active entry already uses this identifier") from None
            if row is None:
                existing = conn.execute(f"SELECT {COLS} FROM watchlist WHERE watchlist_id = %s",
                                        (watchlist_id,)).fetchone()
                if existing is None:
                    raise EntryNotFound(f"no watchlist entry {watchlist_id}")
                return WatchlistEntry(**existing)                  # already active
            self._audit(conn, watchlist_id, "RESTORE", actor)
        return WatchlistEntry(**row)

    def find_exact(self, normalized, entity_types):
        with self._conn() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM watchlist WHERE active AND normalized_identifier = %s "
                                "AND entity_type = ANY(%s) ORDER BY watchlist_id",
                                (normalized, list(entity_types))).fetchall()
        return [WatchlistEntry(**r) for r in rows]

    def find_same_length(self, normalized, entity_types, limit=5000):
        with self._conn() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM watchlist WHERE active AND entity_type = ANY(%s) "
                                "AND char_length(normalized_identifier) = %s ORDER BY watchlist_id LIMIT %s",
                                (list(entity_types), len(normalized), limit)).fetchall()
        return [WatchlistEntry(**r) for r in rows]

    def load_active(self, entity_types):
        with self._conn() as conn:
            rows = conn.execute(f"SELECT {COLS} FROM watchlist WHERE active AND entity_type = ANY(%s) "
                                "ORDER BY watchlist_id", (list(entity_types),)).fetchall()
        return [WatchlistEntry(**r) for r in rows]

    def record_hit(self, hit):
        with self._conn() as conn:
            try:
                row = conn.execute(
                    "INSERT INTO watchlist_hits (watchlist_id, camera_id, track_id, plate, match_type, "
                    "distance, plate_confidence, score, status, event_id, seen_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING hit_id",
                    (hit.watchlist_id, hit.camera_id, hit.track_id, hit.plate, hit.match_type,
                     hit.distance, hit.plate_confidence, hit.score, hit.status, hit.event_id,
                     hit.seen_at)).fetchone()
            except ForeignKeyViolation:
                raise EntryNotFound(f"no watchlist entry {hit.watchlist_id}") from None
        return row["hit_id"]

    def recent_hits(self, limit=50, watchlist_id=None):
        where, params = "", []
        if watchlist_id is not None:
            where, params = "WHERE watchlist_id = %s", [watchlist_id]
        with self._conn() as conn:
            return conn.execute(f"SELECT {HIT_COLS} FROM watchlist_hits {where} "
                                "ORDER BY hit_id DESC LIMIT %s", (*params, limit)).fetchall()

    def audit_log(self, limit=100):
        with self._conn() as conn:
            return conn.execute("SELECT audit_id, watchlist_id, action, actor, details, created_at "
                                "FROM watchlist_audit ORDER BY audit_id DESC LIMIT %s", (limit,)).fetchall()

    def ping(self):
        with self._conn() as conn:
            conn.execute("SELECT 1")

    def close(self):
        self.pool.close()
