import re
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.db.alert_workflow import (ALLOWED, OPEN, STATUSES, AlertNotFound, InvalidTransition, sources_for)
from app.db.records import SEVERITIES, EventRecord
from app.events.envelope import TYPE_RE
from app.watchlist.models import RepoUnavailable

CAMERA_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
CREDENTIALS_RE = re.compile(r"://[^/@]+@")
CAMERA_STATUSES = ("ACTIVE", "INACTIVE", "OFFLINE", "MAINTENANCE", "UNREGISTERED")
EVENT_COLUMNS = ("event_id, event_ref(event_seq) AS event_ref, camera_id, event_type, track_id, severity, "
                 "threat_score, timestamp, snapshot_path, plate_number, object_class, rule_id, rule_kind, "
                 "run_id, metadata, received_at")
ALERT_COLUMNS = ("alert_id, event_id, camera_id, priority, threat_score, status, entity, summary, "
                 "acknowledged_by, acknowledged_at, resolved_at, created_at, updated_at")
MAX_PAGE = 1000


class InvalidRecord(ValueError):
    """The data violates a rule of the schema (retrying will not help)."""


@dataclass
class StoreResult:
    inserted: bool                 # False: the event was already stored (a duplicate delivery)
    alert_created: bool = False
    vehicle_created: bool = False
    detection_created: bool = False
    camera_registered: bool = False


def validate_record(rec: EventRecord) -> None:
    """The schema's rules, checked up front for clear messages (the database enforces them too)."""
    e = rec.event
    if not 1 <= len(e.event_id) <= 64:
        raise InvalidRecord("event_id must be 1-64 characters")
    if not CAMERA_ID_RE.match(e.camera_id):
        raise InvalidRecord(f"invalid camera_id {e.camera_id!r}")
    if not TYPE_RE.match(e.event_type):
        raise InvalidRecord(f"invalid event_type {e.event_type!r}")
    if e.severity is not None and e.severity not in SEVERITIES:
        raise InvalidRecord(f"invalid severity {e.severity!r}")
    if e.threat_score is not None and not 0 <= e.threat_score <= 100:
        raise InvalidRecord("threat_score must be 0-100")


def validate_camera(camera_id: str, rtsp_url: Optional[str], status: str) -> None:
    if not CAMERA_ID_RE.match(camera_id):
        raise InvalidRecord(f"invalid camera_id {camera_id!r}")
    if rtsp_url and CREDENTIALS_RE.search(rtsp_url):
        raise InvalidRecord("rtsp_url must not contain credentials")
    if status not in CAMERA_STATUSES:
        raise InvalidRecord(f"invalid camera status {status!r}")


def _page(limit: int, offset: int):
    return max(1, min(int(limit), MAX_PAGE)), max(0, int(offset))


class EventRepository(ABC):
    @abstractmethod
    def upsert_camera(self, camera_id: str, name: str, location: str = "", rtsp_url: Optional[str] = None,
                      status: str = "ACTIVE", metadata: Optional[dict] = None) -> None:
        """Create or update a camera. A placeholder (UNREGISTERED) becomes real; an operator-set status is kept."""

    @abstractmethod
    def get_camera(self, camera_id: str) -> Optional[dict]: ...

    @abstractmethod
    def list_cameras(self) -> List[dict]: ...

    @abstractmethod
    def store(self, rec: EventRecord) -> StoreResult:
        """Store the event and its derived rows in ONE transaction. Idempotent by event_id."""

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[dict]: ...

    @abstractmethod
    def list_events(self, camera_id=None, event_type=None, severity=None, plate=None, since=None, until=None,
                    limit: int = 100, offset: int = 0) -> List[dict]:
        """Newest first."""

    @abstractmethod
    def count_events(self, camera_id=None, event_type=None, severity=None, plate=None, since=None, until=None) -> int: ...

    @abstractmethod
    def get_alert(self, alert_id: str) -> Optional[dict]: ...

    @abstractmethod
    def list_alerts(self, status=None, priority=None, camera_id=None, limit: int = 100, offset: int = 0) -> List[dict]:
        """Newest first."""

    @abstractmethod
    def alert_counts(self) -> Dict[str, Dict[str, int]]:
        """{priority: {'total', 'new', 'open'}} for every priority (zeros included)."""

    @abstractmethod
    def transition_alert(self, alert_id: str, to_status: str, actor: str, note: str = "") -> dict:
        """Move an alert along the workflow. Raises AlertNotFound or InvalidTransition."""

    @abstractmethod
    def alert_history(self, alert_id: str) -> List[dict]: ...

    @abstractmethod
    def list_vehicles(self, plate: Optional[str] = None, limit: int = 100) -> List[dict]: ...

    @abstractmethod
    def list_detections(self, camera_id: Optional[str] = None, limit: int = 100) -> List[dict]: ...

    @abstractmethod
    def purge(self, events_before: datetime, alerts_before: datetime) -> Dict[str, int]:
        """Delete alerts created before `alerts_before`, then events older than `events_before` that no remaining
        alert refers to (their vehicle and detection rows go with them)."""

    @abstractmethod
    def stats(self) -> dict: ...

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass


# --------------------------------------------------------------------------- in memory
class InMemoryEventRepository(EventRepository):
    """A faithful model of the schema's rules, for fast tests. `fail = True` simulates an outage."""

    def __init__(self):
        self._lock = threading.RLock()
        self.cameras: Dict[str, dict] = {}
        self.events: Dict[str, dict] = {}
        self.alerts: Dict[str, dict] = {}
        self.history: List[dict] = []
        self.vehicles: List[dict] = []
        self.detections: List[dict] = []
        self._seq = 0
        self.fail = False

    def _check(self):
        if self.fail:
            raise RepoUnavailable("simulated database outage")

    # cameras
    def upsert_camera(self, camera_id, name, location="", rtsp_url=None, status="ACTIVE", metadata=None):
        self._check()
        validate_camera(camera_id, rtsp_url, status)
        with self._lock:
            now = datetime.now().astimezone()
            old = self.cameras.get(camera_id)
            keep = old is not None and old["status"] != "UNREGISTERED"
            self.cameras[camera_id] = {"camera_id": camera_id, "name": name, "location": location,
                                       "rtsp_url": rtsp_url, "status": old["status"] if keep else status,
                                       "metadata": dict(metadata or {}), "created_at": old["created_at"] if old else now,
                                       "updated_at": now}

    def get_camera(self, camera_id):
        self._check()
        with self._lock:
            c = self.cameras.get(camera_id)
            return dict(c) if c else None

    def list_cameras(self):
        self._check()
        with self._lock:
            return [dict(c) for _, c in sorted(self.cameras.items())]

    # events
    def store(self, rec):
        self._check()
        validate_record(rec)
        e = rec.event
        with self._lock:
            if e.event_id in self.events:
                return StoreResult(False)
            registered = e.camera_id not in self.cameras
            if registered:
                now = datetime.now().astimezone()
                self.cameras[e.camera_id] = {"camera_id": e.camera_id, "name": e.camera_id, "location": "",
                                             "rtsp_url": None, "status": "UNREGISTERED", "metadata": {},
                                             "created_at": now, "updated_at": now}
            self._seq += 1
            self.events[e.event_id] = {
                "event_id": e.event_id, "event_ref": f"EVT_{self._seq:06d}", "event_seq": self._seq,
                "camera_id": e.camera_id, "event_type": e.event_type, "track_id": e.track_id,
                "severity": e.severity, "threat_score": e.threat_score, "timestamp": e.timestamp,
                "snapshot_path": e.snapshot_path, "plate_number": e.plate_number, "object_class": e.object_class,
                "rule_id": e.rule_id, "rule_kind": e.rule_kind, "run_id": e.run_id, "metadata": dict(e.metadata),
                "received_at": datetime.now().astimezone()}
            result = StoreResult(True, camera_registered=registered)
            if rec.alert and not any(a["event_id"] == e.event_id or a["alert_id"] == rec.alert.alert_id
                                     for a in self.alerts.values()):
                a = rec.alert
                self.alerts[a.alert_id] = {"alert_id": a.alert_id, "event_id": a.event_id, "camera_id": a.camera_id,
                                           "priority": a.priority, "threat_score": a.threat_score, "status": "NEW",
                                           "entity": a.entity, "summary": a.summary, "acknowledged_by": None,
                                           "acknowledged_at": None, "resolved_at": None, "created_at": a.created_at,
                                           "updated_at": datetime.now().astimezone()}
                self.history.append({"alert_id": a.alert_id, "from_status": None, "to_status": "NEW",
                                     "actor": "system", "note": "created from THREAT_ALERT", "at": a.created_at})
                result.alert_created = True
            if rec.vehicle:
                self.vehicles.append({**vars(rec.vehicle), "vehicle_id": len(self.vehicles) + 1})
                result.vehicle_created = True
            if rec.detection:
                self.detections.append({**vars(rec.detection), "detection_id": len(self.detections) + 1})
                result.detection_created = True
            return result

    def get_event(self, event_id):
        self._check()
        with self._lock:
            e = self.events.get(event_id)
            return dict(e) if e else None

    def _filtered(self, camera_id, event_type, severity, plate, since, until):
        rows = [e for e in self.events.values()
                if (not camera_id or e["camera_id"] == camera_id)
                and (not event_type or e["event_type"] == event_type)
                and (not severity or e["severity"] == severity)
                and (not plate or e["plate_number"] == plate)
                and (not since or e["timestamp"] >= since)
                and (not until or e["timestamp"] < until)]
        return sorted(rows, key=lambda r: (r["timestamp"], r["event_seq"]), reverse=True)

    def list_events(self, camera_id=None, event_type=None, severity=None, plate=None, since=None, until=None,
                    limit=100, offset=0):
        self._check()
        limit, offset = _page(limit, offset)
        with self._lock:
            return [dict(r) for r in self._filtered(camera_id, event_type, severity, plate, since, until)[offset:offset + limit]]

    def count_events(self, camera_id=None, event_type=None, severity=None, plate=None, since=None, until=None):
        self._check()
        with self._lock:
            return len(self._filtered(camera_id, event_type, severity, plate, since, until))

    # alerts
    def get_alert(self, alert_id):
        self._check()
        with self._lock:
            a = self.alerts.get(alert_id)
            return dict(a) if a else None

    def list_alerts(self, status=None, priority=None, camera_id=None, limit=100, offset=0):
        self._check()
        limit, offset = _page(limit, offset)
        with self._lock:
            rows = [a for a in self.alerts.values()
                    if (not status or a["status"] == status) and (not priority or a["priority"] == priority)
                    and (not camera_id or a["camera_id"] == camera_id)]
            rows.sort(key=lambda a: (a["created_at"], a["alert_id"]), reverse=True)
            return [dict(a) for a in rows[offset:offset + limit]]

    def alert_counts(self):
        self._check()
        with self._lock:
            out = {p: {"total": 0, "new": 0, "open": 0} for p in SEVERITIES}
            for a in self.alerts.values():
                c = out[a["priority"]]
                c["total"] += 1
                c["new"] += a["status"] == "NEW"
                c["open"] += a["status"] in OPEN
            return out

    def transition_alert(self, alert_id, to_status, actor, note=""):
        self._check()
        if to_status not in STATUSES or to_status == "NEW":
            raise InvalidTransition(f"cannot move an alert to {to_status!r}")
        if not str(actor or "").strip():
            raise InvalidTransition("a person (actor) is required")
        with self._lock:
            a = self.alerts.get(alert_id)
            if a is None:
                raise AlertNotFound(alert_id)
            if a["status"] not in sources_for(to_status):
                raise InvalidTransition(f"cannot move from {a['status']} to {to_status}")
            now = datetime.now().astimezone()
            self.history.append({"alert_id": alert_id, "from_status": a["status"], "to_status": to_status,
                                 "actor": actor, "note": note, "at": now})
            a["status"] = to_status
            a["acknowledged_by"] = a["acknowledged_by"] or actor
            a["acknowledged_at"] = a["acknowledged_at"] or now
            if to_status in ("RESOLVED", "FALSE_POSITIVE"):
                a["resolved_at"] = now
            a["updated_at"] = now
            return dict(a)

    def alert_history(self, alert_id):
        self._check()
        with self._lock:
            return [dict(h) for h in self.history if h["alert_id"] == alert_id]

    # derived
    def list_vehicles(self, plate=None, limit=100):
        self._check()
        with self._lock:
            rows = [v for v in self.vehicles if not plate or v["plate_number"] == plate]
            return [dict(v) for v in sorted(rows, key=lambda v: v["timestamp"], reverse=True)[:max(1, min(limit, MAX_PAGE))]]

    def list_detections(self, camera_id=None, limit=100):
        self._check()
        with self._lock:
            rows = [d for d in self.detections if not camera_id or d["camera_id"] == camera_id]
            return [dict(d) for d in sorted(rows, key=lambda d: d["timestamp"], reverse=True)[:max(1, min(limit, MAX_PAGE))]]

    def purge(self, events_before, alerts_before):
        self._check()
        with self._lock:
            old_alerts = [k for k, a in self.alerts.items() if a["created_at"] < alerts_before]
            for k in old_alerts:
                del self.alerts[k]
            self.history = [h for h in self.history if h["alert_id"] in self.alerts]
            kept = {a["event_id"] for a in self.alerts.values()}
            old_events = [k for k, e in self.events.items() if e["timestamp"] < events_before and k not in kept]
            for k in old_events:
                del self.events[k]
            self.vehicles = [v for v in self.vehicles if v["event_id"] in self.events]
            self.detections = [d for d in self.detections if d["event_id"] in self.events]
            return {"alerts": len(old_alerts), "events": len(old_events)}

    def stats(self):
        self._check()
        with self._lock:
            times = [e["timestamp"] for e in self.events.values()]
            return {"cameras": len(self.cameras), "events": len(self.events), "alerts": len(self.alerts),
                    "vehicles": len(self.vehicles), "detections": len(self.detections),
                    "oldest_event": min(times) if times else None, "newest_event": max(times) if times else None}


# --------------------------------------------------------------------------- PostgreSQL
class PostgresEventRepository(EventRepository):
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 5):
        from psycopg_pool import ConnectionPool
        self._pool = ConnectionPool(dsn, min_size=min_size, max_size=max_size, open=False, timeout=5)
        self._pool.open(wait=False)

    @contextmanager
    def _conn(self):
        import psycopg
        from psycopg.rows import dict_row
        from psycopg_pool import PoolTimeout
        try:
            with self._pool.connection() as conn:                  # one transaction: commit on success, rollback on error
                conn.row_factory = dict_row
                yield conn
        except (psycopg.OperationalError, PoolTimeout) as e:
            raise RepoUnavailable(str(e)) from e

    # cameras
    def upsert_camera(self, camera_id, name, location="", rtsp_url=None, status="ACTIVE", metadata=None):
        from psycopg.types.json import Jsonb
        validate_camera(camera_id, rtsp_url, status)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO cameras (camera_id, name, location, rtsp_url, status, metadata) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (camera_id) DO UPDATE SET name = EXCLUDED.name, location = EXCLUDED.location, "
                "rtsp_url = EXCLUDED.rtsp_url, metadata = EXCLUDED.metadata, updated_at = now(), "
                "status = CASE WHEN cameras.status = 'UNREGISTERED' THEN EXCLUDED.status ELSE cameras.status END",
                (camera_id, name, location, rtsp_url, status, Jsonb(metadata or {})))

    def get_camera(self, camera_id):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM cameras WHERE camera_id = %s", (camera_id,)).fetchone()

    def list_cameras(self):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM cameras ORDER BY camera_id").fetchall()

    # events
    def store(self, rec):
        import psycopg
        from psycopg.types.json import Jsonb
        validate_record(rec)
        e = rec.event
        try:
            with self._conn() as conn:
                registered = conn.execute(
                    "INSERT INTO cameras (camera_id, name, status) VALUES (%s, %s, 'UNREGISTERED') "
                    "ON CONFLICT (camera_id) DO NOTHING RETURNING camera_id", (e.camera_id, e.camera_id)).fetchone() is not None
                row = conn.execute(
                    "INSERT INTO events (event_id, camera_id, event_type, track_id, severity, threat_score, timestamp, "
                    "snapshot_path, plate_number, object_class, rule_id, rule_kind, run_id, metadata) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (event_id) DO NOTHING RETURNING event_id",
                    (e.event_id, e.camera_id, e.event_type, e.track_id, e.severity, e.threat_score, e.timestamp,
                     e.snapshot_path, e.plate_number, e.object_class, e.rule_id, e.rule_kind, e.run_id,
                     Jsonb(e.metadata))).fetchone()
                if row is None:
                    return StoreResult(False)                      # already stored: nothing else to do
                result = StoreResult(True, camera_registered=registered)
                if rec.alert:
                    a = rec.alert
                    result.alert_created = conn.execute(
                        "INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, entity, summary, created_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING alert_id",
                        (a.alert_id, a.event_id, a.camera_id, a.priority, a.threat_score, a.entity, a.summary,
                         a.created_at)).fetchone() is not None
                    if result.alert_created:
                        conn.execute("INSERT INTO alert_history (alert_id, from_status, to_status, actor, note, at) "
                                     "VALUES (%s, NULL, 'NEW', 'system', 'created from THREAT_ALERT', %s)",
                                     (a.alert_id, a.created_at))
                if rec.vehicle:
                    v = rec.vehicle
                    result.vehicle_created = conn.execute(
                        "INSERT INTO vehicles (event_id, camera_id, track_id, plate_number, confidence, timestamp, "
                        "vehicle_class, final, plate_format) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT (event_id) DO NOTHING RETURNING vehicle_id",
                        (v.event_id, v.camera_id, v.track_id, v.plate_number, v.confidence, v.timestamp,
                         v.vehicle_class, v.final, v.plate_format)).fetchone() is not None
                if rec.detection:
                    d = rec.detection
                    result.detection_created = conn.execute(
                        "INSERT INTO detections (event_id, camera_id, track_id, object_type, confidence, timestamp, "
                        "first_seen, last_seen, duration_s, hits, bbox) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT (event_id) DO NOTHING RETURNING detection_id",
                        (d.event_id, d.camera_id, d.track_id, d.object_type, d.confidence, d.timestamp, d.first_seen,
                         d.last_seen, d.duration_s, d.hits, Jsonb(d.bbox) if d.bbox is not None else None)).fetchone() is not None
                return result
        except (psycopg.errors.IntegrityError, psycopg.errors.DataError) as ex:
            raise InvalidRecord(str(ex).splitlines()[0]) from None

    def get_event(self, event_id):
        with self._conn() as conn:
            return conn.execute(f"SELECT {EVENT_COLUMNS} FROM events WHERE event_id = %s", (event_id,)).fetchone()

    @staticmethod
    def _event_where(camera_id, event_type, severity, plate, since, until):
        clauses, params = [], []
        for column, value in (("camera_id", camera_id), ("event_type", event_type), ("severity", severity),
                              ("plate_number", plate)):
            if value:
                clauses.append(f"{column} = %s")
                params.append(value)
        if since:
            clauses.append("timestamp >= %s")
            params.append(since)
        if until:
            clauses.append("timestamp < %s")
            params.append(until)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def list_events(self, camera_id=None, event_type=None, severity=None, plate=None, since=None, until=None,
                    limit=100, offset=0):
        limit, offset = _page(limit, offset)
        where, params = self._event_where(camera_id, event_type, severity, plate, since, until)
        with self._conn() as conn:
            return conn.execute(f"SELECT {EVENT_COLUMNS} FROM events{where} ORDER BY timestamp DESC, event_seq DESC "
                                "LIMIT %s OFFSET %s", params + [limit, offset]).fetchall()

    def count_events(self, camera_id=None, event_type=None, severity=None, plate=None, since=None, until=None):
        where, params = self._event_where(camera_id, event_type, severity, plate, since, until)
        with self._conn() as conn:
            return int(conn.execute(f"SELECT count(*) AS n FROM events{where}", params).fetchone()["n"])

    # alerts
    def get_alert(self, alert_id):
        with self._conn() as conn:
            return conn.execute(f"SELECT {ALERT_COLUMNS} FROM alerts WHERE alert_id = %s", (alert_id,)).fetchone()

    def list_alerts(self, status=None, priority=None, camera_id=None, limit=100, offset=0):
        limit, offset = _page(limit, offset)
        clauses, params = [], []
        for column, value in (("status", status), ("priority", priority), ("camera_id", camera_id)):
            if value:
                clauses.append(f"{column} = %s")
                params.append(value)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            return conn.execute(f"SELECT {ALERT_COLUMNS} FROM alerts{where} ORDER BY created_at DESC, alert_id DESC "
                                "LIMIT %s OFFSET %s", params + [limit, offset]).fetchall()

    def alert_counts(self):
        out = {p: {"total": 0, "new": 0, "open": 0} for p in SEVERITIES}
        with self._conn() as conn:
            for r in conn.execute("SELECT priority, total, new_count, open_count FROM alert_counts").fetchall():
                out[r["priority"]] = {"total": r["total"], "new": r["new_count"], "open": r["open_count"]}
        return out

    def transition_alert(self, alert_id, to_status, actor, note=""):
        if to_status not in STATUSES or to_status == "NEW":
            raise InvalidTransition(f"cannot move an alert to {to_status!r}")
        if not str(actor or "").strip():
            raise InvalidTransition("a person (actor) is required")
        with self._conn() as conn:
            cur = conn.execute("SELECT status FROM alerts WHERE alert_id = %s FOR UPDATE", (alert_id,)).fetchone()
            if cur is None:
                raise AlertNotFound(alert_id)                       # the row lock serializes concurrent decisions
            if cur["status"] not in sources_for(to_status):
                raise InvalidTransition(f"cannot move from {cur['status']} to {to_status}")
            row = conn.execute(
                "UPDATE alerts SET status = %s, acknowledged_by = COALESCE(acknowledged_by, %s), "
                "acknowledged_at = COALESCE(acknowledged_at, now()), "
                "resolved_at = CASE WHEN %s IN ('RESOLVED', 'FALSE_POSITIVE') THEN now() ELSE resolved_at END, "
                f"updated_at = now() WHERE alert_id = %s RETURNING {ALERT_COLUMNS}",
                (to_status, actor, to_status, alert_id)).fetchone()
            conn.execute("INSERT INTO alert_history (alert_id, from_status, to_status, actor, note) "
                         "VALUES (%s, %s, %s, %s, %s)", (alert_id, cur["status"], to_status, actor, note))
            return row

    def alert_history(self, alert_id):
        with self._conn() as conn:
            return conn.execute("SELECT alert_id, from_status, to_status, actor, note, at FROM alert_history "
                                "WHERE alert_id = %s ORDER BY history_id", (alert_id,)).fetchall()

    # derived
    def list_vehicles(self, plate=None, limit=100):
        with self._conn() as conn:
            if plate:
                return conn.execute("SELECT * FROM vehicles WHERE plate_number = %s ORDER BY timestamp DESC LIMIT %s",
                                    (plate, max(1, min(limit, MAX_PAGE)))).fetchall()
            return conn.execute("SELECT * FROM vehicles ORDER BY timestamp DESC LIMIT %s",
                                (max(1, min(limit, MAX_PAGE)),)).fetchall()

    def list_detections(self, camera_id=None, limit=100):
        with self._conn() as conn:
            if camera_id:
                return conn.execute("SELECT * FROM detections WHERE camera_id = %s ORDER BY timestamp DESC LIMIT %s",
                                    (camera_id, max(1, min(limit, MAX_PAGE)))).fetchall()
            return conn.execute("SELECT * FROM detections ORDER BY timestamp DESC LIMIT %s",
                                (max(1, min(limit, MAX_PAGE)),)).fetchall()

    def purge(self, events_before, alerts_before):
        with self._conn() as conn:
            alerts = conn.execute("WITH d AS (DELETE FROM alerts WHERE created_at < %s RETURNING 1) "
                                  "SELECT count(*) AS n FROM d", (alerts_before,)).fetchone()["n"]
            events = conn.execute(
                "WITH d AS (DELETE FROM events e WHERE e.timestamp < %s AND NOT EXISTS "
                "(SELECT 1 FROM alerts a WHERE a.event_id = e.event_id) RETURNING 1) "
                "SELECT count(*) AS n FROM d", (events_before,)).fetchone()["n"]
            return {"alerts": int(alerts), "events": int(events)}

    def stats(self):
        with self._conn() as conn:
            out = {t: int(conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"])
                   for t in ("cameras", "events", "alerts", "vehicles", "detections")}
            span = conn.execute("SELECT min(timestamp) AS oldest, max(timestamp) AS newest FROM events").fetchone()
            out["oldest_event"], out["newest_event"] = span["oldest"], span["newest"]
            return out

    def ping(self):
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
            return True
        except RepoUnavailable:
            return False

    def close(self):
        self._pool.close()
