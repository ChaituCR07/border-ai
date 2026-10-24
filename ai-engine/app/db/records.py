from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.events.envelope import Envelope

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class MappingError(ValueError):
    """The event cannot be stored as it is (retrying will not help)."""


@dataclass
class EventRow:
    event_id: str
    camera_id: str
    event_type: str
    track_id: int
    severity: Optional[str]
    threat_score: Optional[int]
    timestamp: datetime
    snapshot_path: Optional[str]
    plate_number: Optional[str]
    object_class: Optional[str]
    rule_id: Optional[str]
    rule_kind: Optional[str]
    run_id: str
    metadata: dict


@dataclass
class AlertRow:
    alert_id: str
    event_id: str
    camera_id: str
    priority: str
    threat_score: int
    entity: str
    summary: str
    created_at: datetime


@dataclass
class VehicleRow:
    event_id: str
    camera_id: str
    track_id: int
    plate_number: str
    confidence: float
    timestamp: datetime
    vehicle_class: Optional[str]
    final: bool
    plate_format: Optional[str]


@dataclass
class DetectionRow:
    event_id: str
    camera_id: str
    track_id: int
    object_type: str
    confidence: float
    timestamp: datetime
    first_seen: datetime
    last_seen: datetime
    duration_s: float
    hits: int
    bbox: Optional[list]


@dataclass
class EventRecord:
    event: EventRow
    alert: Optional[AlertRow] = None
    vehicle: Optional[VehicleRow] = None
    detection: Optional[DetectionRow] = None


def parse_time(value) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise MappingError(f"invalid timestamp {value!r}") from None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _unit(value, name) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise MappingError(f"{name} is not a number") from None
    return min(1.0, max(0.0, x))


def _score(value, name) -> int:
    try:
        x = int(round(float(value)))
    except (TypeError, ValueError):
        raise MappingError(f"{name} is not a number") from None
    return min(100, max(0, x))


def map_envelope(env: Envelope) -> EventRecord:
    """Envelope -> the rows to store. Raises MappingError for events that can never be stored."""
    d = env.data
    details = d.get("details") or {}
    obj = d.get("object") or {}
    rule = d.get("rule") or {}
    ts = parse_time(d.get("timestamp"))

    raw_sev = str(env.severity or details.get("severity") or "").upper()
    severity = raw_sev if raw_sev in SEVERITIES else None                      # tolerant: unknown -> NULL

    snapshot = details.get("snapshot_path")
    snapshot_path = f"{env.run_id}/{snapshot}" if snapshot and env.run_id else (snapshot or None)
    plate = d.get("plate") or details.get("plate") or None

    threat_score = None
    if env.type == "THREAT_ALERT":
        threat_score = _score(details.get("threat_score", d.get("threat_score")), "threat_score")

    event = EventRow(env.event_id, env.camera, env.type, int(d["track_id"]), severity, threat_score, ts,
                     snapshot_path, str(plate) if plate else None, obj.get("class"), rule.get("id"),
                     rule.get("kind"), env.run_id, env.data)
    record = EventRecord(event)

    if env.type == "THREAT_ALERT":
        alert_id = str(details.get("alert_id") or "").strip()
        if not alert_id:
            raise MappingError("THREAT_ALERT without an alert_id")
        priority = str(details.get("priority") or details.get("level") or "").upper()
        if priority not in SEVERITIES:
            raise MappingError(f"THREAT_ALERT with an invalid priority {priority!r}")
        record.alert = AlertRow(alert_id, env.event_id, env.camera, priority, threat_score,
                                str(details.get("entity") or ""), str(details.get("summary") or "")[:2000], ts)

    elif env.type == "PLATE_RECOGNIZED" and plate:
        record.vehicle = VehicleRow(env.event_id, env.camera, event.track_id, str(plate),
                                    _unit(obj.get("confidence", 0.0), "confidence"), ts, obj.get("class"),
                                    bool(details.get("final", False)), details.get("format"))

    elif env.type == "TRACK_SUMMARY":
        first = parse_time(details.get("first_seen"))
        last = parse_time(details.get("last_seen"))
        record.detection = DetectionRow(env.event_id, env.camera, event.track_id, obj.get("class") or "unknown",
                                        _unit(details.get("max_confidence", obj.get("confidence", 0.0)), "confidence"),
                                        ts, first, last, max(0.0, float(details.get("duration_s", 0.0))),
                                        max(0, int(details.get("hits", 0))), obj.get("bbox"))
    return record
