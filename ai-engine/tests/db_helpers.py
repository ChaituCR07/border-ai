from datetime import datetime, timezone

from app.db.records import map_envelope
from app.events.envelope import envelope_from_event
from app.schemas.events import Event
from behaviour_helpers import epoch, obs

T0 = epoch("2026-10-12 02:13:00")


def utc(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def to_record(event, run_id="RUN1"):
    return map_envelope(envelope_from_event(event, run_id))


def zone_event(i=0, cam="CAM_1", track=1, severity="HIGH", ts=None):
    details = {"severity": severity} if severity else {}
    return obs("ZONE_VIOLATION", ts if ts is not None else T0 + i, track=track, cam=cam, rule_id="R001",
               rule_kind="behaviour", details=details)


def alert_event(i=0, score=60, level="HIGH", alert_id=None, cam="CAM_1", track=1, plate=None, entity="CAM_1#1",
                snapshot="snapshots/a1.jpg"):
    details = {"alert_id": alert_id or f"ALR_{i:05d}", "threat_score": score, "level": level, "priority": level,
               "severity": level, "summary": f"{level} threat", "entity": entity, "snapshot_path": snapshot}
    if plate:
        details["plate"] = plate
    return obs("THREAT_ALERT", T0 + i, track=track, cam=cam, rule_id="THREAT", rule_kind="threat", details=details)


def plate_event(i=0, plate="KA01AB1234", cam="CAM_1", track=2, confidence=0.9, final=True):
    e = obs("PLATE_RECOGNIZED", T0 + i, track=track, cam=cam, rule_id="ANPR", rule_kind="anpr",
            details={"plate": plate, "final": final, "format": "strict"})
    e.confidence = confidence
    return e


def summary_event(i=0, cam="CAM_1", track=3, cls="person", hits=40, duration=12.0):
    return obs("TRACK_SUMMARY", T0 + i + duration, track=track, cam=cam, rule_id="TRACK", rule_kind="track",
               details={"first_seen": utc(T0 + i).isoformat().replace("+00:00", "Z"),
                        "last_seen": utc(T0 + i + duration).isoformat().replace("+00:00", "Z"),
                        "duration_s": duration, "hits": hits, "max_confidence": 0.88}, cls=cls)
