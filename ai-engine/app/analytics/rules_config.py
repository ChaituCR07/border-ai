import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from shapely.geometry import Polygon

log = logging.getLogger("rules")

ANCHORS = ("bottom_center", "center")
DIRECTIONS = ("IN", "OUT")


def opposite(direction: str) -> str:
    return "OUT" if direction == "IN" else "IN"


@dataclass
class ZoneRule:
    id: str
    name: str
    polygon: List[Tuple[float, float]]             # normalized 0-1
    type: str = "monitored"
    classes: Optional[List[str]] = None
    anchor: str = "bottom_center"
    min_frames_inside: int = 3
    min_frames_outside: int = 5
    dwell_alert_s: float = 0.0
    loiter_s: float = 0.0
    loiter_max_span: float = 0.08                  # fraction of frame width


@dataclass
class LineRule:
    id: str
    name: str
    p1: Tuple[float, float]                        # normalized 0-1
    p2: Tuple[float, float]
    positive_direction: str = "IN"
    type: str = "tripwire"
    classes: Optional[List[str]] = None
    anchor: str = "bottom_center"
    hysteresis: float = 0.01                       # fraction of frame width
    cooldown_s: float = 2.0


@dataclass
class CameraRules:
    camera_id: str
    zones: List[ZoneRule] = field(default_factory=list)
    lines: List[LineRule] = field(default_factory=list)
    min_track_hits: int = 3


def _point(value, where: str, ref=None) -> Tuple[float, float]:
    try:
        x, y = float(value[0]), float(value[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError(f"{where}: a point must be [x, y], got {value!r}")
    if (x > 1.0 or y > 1.0) and ref:                     # pixel coordinates -> normalize
        x, y = x / ref["width"], y / ref["height"]
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        raise ValueError(f"{where}: point {value!r} is outside the frame "
                         f"(use 0-1 values, or pixels together with reference_size)")
    return (x, y)


def _check_anchor(anchor: str, where: str) -> str:
    if anchor not in ANCHORS:
        raise ValueError(f"{where}: anchor must be one of {ANCHORS}, got {anchor!r}")
    return anchor


def parse_camera_rules(data: dict, source: str = "<dict>") -> CameraRules:
    camera_id = data.get("camera_id")
    if not camera_id:
        raise ValueError(f"{source}: missing camera_id")

    ref = data.get("reference_size")
    if ref is not None and not (ref.get("width", 0) > 0 and ref.get("height", 0) > 0):
        raise ValueError(f"{source}: reference_size needs positive width and height")

    rules = CameraRules(camera_id=camera_id,
                        min_track_hits=int(data.get("min_track_hits", 3)))
    seen_ids = set()

    for i, z in enumerate(data.get("zones", []), 1):
        zid = z.get("id", f"Z{i}")
        where = f"{source} zone {zid}"
        if zid in seen_ids:
            raise ValueError(f"{where}: duplicate id")
        seen_ids.add(zid)

        polygon = [_point(p, where, ref) for p in z.get("polygon", [])]
        if len(polygon) < 3:
            raise ValueError(f"{where}: a zone needs at least 3 points")
        shape = Polygon(polygon)
        if not shape.is_valid or shape.area <= 0:
            raise ValueError(f"{where}: polygon is self-intersecting or has no area")

        min_in = int(z.get("min_frames_inside", 3))
        min_out = int(z.get("min_frames_outside", 5))
        if min_in < 1 or min_out < 1:
            raise ValueError(f"{where}: min_frames_inside/outside must be >= 1")

        rules.zones.append(ZoneRule(
            id=zid, name=z.get("name", zid), polygon=polygon,
            type=z.get("type", "monitored"), classes=z.get("classes"),
            anchor=_check_anchor(z.get("anchor", "bottom_center"), where),
            min_frames_inside=min_in, min_frames_outside=min_out,
            dwell_alert_s=float(z.get("dwell_alert_s", 0.0)),
            loiter_s=float(z.get("loiter_s", 0.0)),
            loiter_max_span=float(z.get("loiter_max_span", 0.08))))

    for i, ln in enumerate(data.get("lines", []), 1):
        lid = ln.get("id", f"L{i}")
        where = f"{source} line {lid}"
        if lid in seen_ids:
            raise ValueError(f"{where}: duplicate id")
        seen_ids.add(lid)

        p1, p2 = _point(ln.get("p1"), where, ref), _point(ln.get("p2"), where, ref)
        if p1 == p2:
            raise ValueError(f"{where}: p1 and p2 are identical")
        direction = str(ln.get("positive_direction", "IN")).upper()
        if direction not in DIRECTIONS:
            raise ValueError(f"{where}: positive_direction must be IN or OUT")
        hysteresis = float(ln.get("hysteresis", 0.01))
        cooldown = float(ln.get("cooldown_s", 2.0))
        if hysteresis < 0 or cooldown < 0:
            raise ValueError(f"{where}: hysteresis and cooldown_s must be >= 0")

        rules.lines.append(LineRule(
            id=lid, name=ln.get("name", lid), p1=p1, p2=p2,
            positive_direction=direction, type=ln.get("type", "tripwire"),
            classes=ln.get("classes"),
            anchor=_check_anchor(ln.get("anchor", "bottom_center"), where),
            hysteresis=hysteresis, cooldown_s=cooldown))

    return rules


def load_camera_rules(path: Path) -> CameraRules:
    with open(path, "r") as f:
        data = json.load(f)
    return parse_camera_rules(data, source=str(path))
