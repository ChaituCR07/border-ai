import json
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Tuple

from app.schemas.events import Event
from app.schemas.tracking import FrameTracks, TrackedObject


def event_from_dict(d: dict) -> Event:
    ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp()
    obj, rule = d.get("object", {}), d.get("rule", {})
    return Event(type=d["type"], camera_id=d["camera_id"], timestamp=ts, frame_id=d.get("frame_id", 0),
                 track_id=d["track_id"], object_class=obj.get("class", "unknown"),
                 confidence=obj.get("confidence", 0.0), bbox=tuple(obj.get("bbox", (0, 0, 1, 1))),
                 rule_id=rule.get("id", ""), rule_name=rule.get("name", ""), rule_kind=rule.get("kind", ""),
                 rule_type=rule.get("type", ""), direction=d.get("direction"), dwell_s=d.get("dwell_s"),
                 details=d.get("details", {}), event_id=d.get("event_id", ""))


def load_events(path) -> List[Event]:
    with open(path, encoding="utf-8") as f:
        return [event_from_dict(json.loads(line)) for line in f if line.strip()]


def replay(events: List[Event], engine, tick_s: float = 1.0, grace_s: float = 5.0,
           keep_behaviour: bool = False) -> List[Event]:
    """Feed recorded observations through the engine. A track counts as present from its first event
    until `grace_s` after its last event. Behaviour events in the recording are skipped, so you can
    compare an old rule set with a new one on the same recording."""
    events = sorted((e for e in events if keep_behaviour or e.rule_kind != "behaviour"), key=lambda e: e.timestamp)
    if not events:
        return []
    spans: Dict[Tuple[str, int], dict] = {}
    for e in events:
        s = spans.setdefault((e.camera_id, e.track_id), {"first": e.timestamp, "last": e.timestamp,
                                                         "cls": e.object_class, "bbox": e.bbox})
        s["last"], s["bbox"] = e.timestamp, e.bbox
        if s["cls"] == "unknown":
            s["cls"] = e.object_class

    out: List[Event] = []
    cameras = sorted({c for c, _ in spans})
    frame, idx, t = 0, 0, events[0].timestamp
    end = events[-1].timestamp + grace_s + tick_s
    ended = set()
    while t <= end:
        while idx < len(events) and events[idx].timestamp <= t:
            engine.observe(events[idx].camera_id, [events[idx]])
            idx += 1
        frame += 1
        for cam in cameras:
            present, removed = [], []
            for (c, tid), s in spans.items():
                if c != cam:
                    continue
                if s["first"] <= t <= s["last"] + grace_s:
                    o = TrackedObject(tid, 0, s["cls"], 0.9, *s["bbox"])
                    o.age_s = t - s["first"]
                    present.append(o)
                elif t > s["last"] + grace_s and (c, tid) not in ended:
                    ended.add((c, tid))
                    removed.append(SimpleNamespace(track_id=tid))
            out += engine.update(FrameTracks(cam, frame, t, 1280, 720, present),
                                 SimpleNamespace(removed=removed))
        t += tick_s
    return out
