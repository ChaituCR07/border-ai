import json

import numpy as np

from app.analytics.engine import RuleEngine
from app.analytics.rules_config import parse_camera_rules
from app.pipeline.visualizer import FlashState, draw_event_feed, draw_lines, draw_zones
from app.schemas.events import Event
from app.schemas.tracking import FrameTracks
from app.tracking.track_store import TrackStore
from rules_helpers import H, W, obj


def write_rules(tmp_path, camera_id="C1"):
    data = {"camera_id": camera_id,
            "zones": [{"id": "Z1", "polygon": [[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75]]}],
            "lines": [{"id": "L1", "p1": [0, 0.5], "p2": [1, 0.5]}]}
    (tmp_path / f"{camera_id}.json").write_text(json.dumps(data))


def run(engine, camera_id, steps):
    store = TrackStore(camera_id, max_lost_frames=30)
    events, t = [], 0.0
    for i, objs in enumerate(steps, 1):
        upd = store.update(objs, t)
        events += engine.update(FrameTracks(camera_id, i, t, W, H, objs), upd, store)
        t += 0.1
    return events


def test_rule_engine_produces_zone_and_line_events(tmp_path):
    write_rules(tmp_path)
    engine = RuleEngine(tmp_path)
    steps = [[obj(1, 320, y)] for y in range(100, 390, 10)]
    events = run(engine, "C1", steps)
    kinds = {e.type for e in events}
    assert "LINE_CROSSING" in kinds and "ZONE_ENTER" in kinds
    assert all(e.camera_id == "C1" for e in events)
    assert engine.stats("C1")["line_counts"]["L1"]["IN"] == 1


def test_camera_without_rules_file_produces_no_events(tmp_path):
    engine = RuleEngine(tmp_path)
    steps = [[obj(1, 320, y)] for y in range(100, 390, 10)]
    assert run(engine, "UNKNOWN", steps) == []
    assert engine.rules_for("UNKNOWN").zones == []


def test_event_to_dict_contract():
    e = Event("LINE_CROSSING", "C1", 1_700_000_000.0, 7, 3, "person", 0.9123,
              (1.04, 2.0, 3.0, 4.0), "L1", "Entry", "line", "tripwire", direction="IN")
    d = e.to_dict()
    assert d["event"] == "LINE_CROSSING"
    assert d["type"] == "LINE_CROSSING" and d["direction"] == "IN"
    assert d["timestamp"].endswith("Z")
    assert d["object"] == {"class": "person", "confidence": 0.912, "bbox": [1.0, 2.0, 3.0, 4.0]}
    assert d["rule"] == {"id": "L1", "name": "Entry", "kind": "line", "type": "tripwire"}
    assert len(d["event_id"]) == 32


def test_flash_state_expires():
    f = FlashState(duration_s=1.5)
    e = Event("ZONE_ENTER", "C1", 0.0, 1, 1, "person", 0.9, (0, 0, 1, 1), "Z1", "Z", "zone", "restricted")
    f.trigger([e], now=10.0)
    assert f.active("Z1", 10.5) and not f.active("Z1", 12.0) and not f.active("other", 10.5)


def test_overlays_draw_without_crashing(tmp_path):
    write_rules(tmp_path)
    rules = parse_camera_rules(json.loads((tmp_path / "C1.json").read_text()))
    img = np.zeros((480, 640, 3), np.uint8)
    flash = FlashState()
    draw_zones(img, rules, {"Z1": 2}, flash, 0.0)
    assert img.any()
    img2 = np.zeros((480, 640, 3), np.uint8)
    draw_lines(img2, rules, {"L1": {"IN": 1, "OUT": 0}}, flash, 0.0)
    assert img2.any()
    draw_event_feed(img2, ["00:01.0 ZONE_ENTER Z1"])


def test_overlays_with_no_rules_are_noops():
    rules = parse_camera_rules({"camera_id": "C1"})
    img = np.zeros((100, 100, 3), np.uint8)
    draw_zones(img, rules, {}, FlashState(), 0.0)
    draw_lines(img, rules, {}, FlashState(), 0.0)
    assert not img.any()
