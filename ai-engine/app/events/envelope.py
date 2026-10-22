import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from app.schemas.events import Event

SCHEMA_VERSION = 1
MAX_DATA_BYTES = 64 * 1024
TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,60}$")


class InvalidEnvelope(ValueError):
    """The message cannot be understood. Retrying will not help."""


@dataclass
class Envelope:
    v: int
    event_id: str
    type: str
    camera: str
    ts_ms: int                    # event time in epoch milliseconds
    severity: str                 # '' when the event has none
    run_id: str                   # which pipeline run produced it
    data: dict                    # the full event JSON

    def to_fields(self) -> Dict[str, str]:
        return {"v": str(self.v), "event_id": self.event_id, "type": self.type, "camera": self.camera,
                "ts": str(self.ts_ms), "severity": self.severity, "run_id": self.run_id,
                "data": json.dumps(self.data, separators=(",", ":"))}


def _iso_to_epoch(text: str) -> float:
    return datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()


def envelope_from_dict(d: dict, run_id: str = "") -> Envelope:
    """Build an envelope from an event dictionary (an `Event.to_dict()` result or a journal line)."""
    data = dict(d)
    data.setdefault("camera", d.get("camera_id", ""))          # the plan's field name
    data["schema"] = SCHEMA_VERSION
    severity = d.get("severity") or (d.get("details") or {}).get("severity") or ""
    return Envelope(SCHEMA_VERSION, d["event_id"], d["type"], d.get("camera_id", ""),
                    int(_iso_to_epoch(d["timestamp"]) * 1000), str(severity), run_id, data)


def envelope_from_event(ev: Event, run_id: str = "") -> Envelope:
    return envelope_from_dict(ev.to_dict(), run_id)


def parse_envelope(fields: Dict[str, str]) -> Envelope:
    """Validate a stream entry and return the envelope. Raises InvalidEnvelope with a short reason."""
    try:
        v = int(fields.get("v", ""))
    except (TypeError, ValueError):
        raise InvalidEnvelope("missing_or_invalid_version") from None
    if v != SCHEMA_VERSION:
        raise InvalidEnvelope(f"unsupported_version:{v}")

    raw = fields.get("data")
    if not isinstance(raw, str) or not raw:
        raise InvalidEnvelope("missing_data")
    if len(raw.encode("utf-8")) > MAX_DATA_BYTES:
        raise InvalidEnvelope("data_too_large")
    try:
        data = json.loads(raw)
    except ValueError:
        raise InvalidEnvelope("data_not_json") from None
    if not isinstance(data, dict):
        raise InvalidEnvelope("data_not_an_object")

    event_id = str(fields.get("event_id", "")).strip()
    etype = str(fields.get("type", ""))
    camera = str(fields.get("camera", "")).strip()
    if not 1 <= len(event_id) <= 64:
        raise InvalidEnvelope("invalid_event_id")
    if not TYPE_RE.match(etype):
        raise InvalidEnvelope("invalid_type")
    if not camera or len(camera) > 64:
        raise InvalidEnvelope("invalid_camera")
    try:
        ts_ms = int(fields.get("ts", ""))
    except (TypeError, ValueError):
        raise InvalidEnvelope("invalid_timestamp") from None
    if data.get("event_id") != event_id or data.get("type") != etype:
        raise InvalidEnvelope("envelope_and_data_disagree")
    if not isinstance(data.get("track_id"), int) or isinstance(data.get("track_id"), bool):
        raise InvalidEnvelope("missing_track_id")
    try:
        _iso_to_epoch(data.get("timestamp"))
    except (TypeError, ValueError):
        raise InvalidEnvelope("invalid_data_timestamp") from None

    return Envelope(v, event_id, etype, camera, ts_ms, str(fields.get("severity", "")),
                    str(fields.get("run_id", "")), data)
