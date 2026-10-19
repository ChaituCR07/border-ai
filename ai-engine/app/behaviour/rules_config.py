import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from app.behaviour.timeutil import DAYS, get_zone, parse_hhmm
from app.watchlist.models import ENTITY_TYPES, RISK_LEVELS

SEVERITIES = RISK_LEVELS
RESERVED_EVENT_TYPES = {"ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL", "LOITERING", "LINE_CROSSING",
                        "PLATE_RECOGNIZED", "WATCHLIST_MATCH", "REID_MATCH"}
EVENT_TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,40}$")

CONDITION_KEYS = {
    "object": {"type", "value"},
    "zone": {"type", "zone_id", "zone_type", "inside", "min_dwell_s"},
    "line_crossing": {"type", "line", "direction", "expected_direction", "within_s"},
    "event": {"type", "event", "where", "within_s"},
    "time": {"type", "between", "days", "timezone"},
    "watchlist": {"type", "present", "status", "risk_level_min", "entity_types"},
    "plate": {"type", "read", "authorized"},
    "track_age": {"type", "min_s"},
    "all": {"type", "conditions"},
    "any": {"type", "conditions"},
    "not": {"type", "condition"},
}


@dataclass
class Rule:
    rule_id: str
    name: str
    event_type: str
    conditions: List[dict]
    severity: str
    points: int
    enabled: bool = True
    cameras: Optional[List[str]] = None
    cooldown_s: float = 0.0
    rearm_s: float = 30.0
    description: str = ""


@dataclass
class BehaviourConfig:
    timezone: str = "UTC"
    camera_timezones: Dict[str, str] = field(default_factory=dict)
    authorized_plates_csv: str = ""
    rules: List[Rule] = field(default_factory=list)


# ----------------------------------------------------------------------------- helpers
def _number(value, where, name, minimum=0.0, default=None) -> float:
    if value is None:
        if default is None:
            raise ValueError(f"{where}: '{name}' is required")
        return float(default)
    if isinstance(value, bool):
        raise ValueError(f"{where}: '{name}' must be a number")
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{where}: '{name}' must be a number") from None
    if x < minimum:
        raise ValueError(f"{where}: '{name}' must be >= {minimum}")
    return x


def _bool(value, where, name, default) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{where}: '{name}' must be true or false")
    return value


def _str_list(value, where, name, allowed=None, upper=False) -> List[str]:
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list) or not items or not all(isinstance(x, str) and x.strip() for x in items):
        raise ValueError(f"{where}: '{name}' must be a non-empty string or list of strings")
    items = [x.strip().upper() if upper else x.strip() for x in items]
    if allowed is not None:
        bad = [x for x in items if x not in allowed]
        if bad:
            raise ValueError(f"{where}: '{name}' has invalid values {bad}; allowed: {sorted(allowed)}")
    return items


# ----------------------------------------------------------------------------- conditions
def validate_condition(node, where: str) -> dict:
    """Check one condition (recursively) and return it with defaults filled in."""
    if not isinstance(node, dict) or "type" not in node:
        raise ValueError(f"{where}: a condition must be an object with a 'type'")
    t = node["type"]
    if t not in CONDITION_KEYS:
        raise ValueError(f"{where}: unknown condition type {t!r}; known types: {sorted(CONDITION_KEYS)}")
    extra = set(node) - CONDITION_KEYS[t]
    if extra:
        raise ValueError(f"{where}: unknown keys {sorted(extra)} for a '{t}' condition")

    out = dict(node)
    at = f"{where} ({t})"
    if t == "object":
        out["value"] = _str_list(node.get("value"), at, "value")
    elif t == "zone":
        if not node.get("zone_id") and not node.get("zone_type"):
            raise ValueError(f"{at}: give 'zone_id' or 'zone_type' (use \"any\" for every zone)")
        out["inside"] = _bool(node.get("inside"), at, "inside", True)
        out["min_dwell_s"] = _number(node.get("min_dwell_s"), at, "min_dwell_s", 0.0, 0.0)
    elif t == "line_crossing":
        for key in ("direction", "expected_direction"):
            if node.get(key) is not None:
                out[key] = _str_list(node[key], at, key, allowed=("IN", "OUT"), upper=True)[0]
        if "direction" in out and "expected_direction" in out:
            raise ValueError(f"{at}: use either 'direction' or 'expected_direction', not both")
        out["within_s"] = _number(node.get("within_s"), at, "within_s", 0.001, 5.0)
    elif t == "event":
        if not isinstance(node.get("event"), str) or not node["event"].strip():
            raise ValueError(f"{at}: 'event' (an event type name) is required")
        out["event"] = node["event"].strip().upper()
        where_map = node.get("where", {})
        if not isinstance(where_map, dict) or not all(isinstance(v, (str, int, float, bool)) for v in where_map.values()):
            raise ValueError(f"{at}: 'where' must map field names to simple values")
        out["where"] = where_map
        out["within_s"] = _number(node.get("within_s"), at, "within_s", 0.001, 10.0)
    elif t == "time":
        window = node.get("between")
        if not isinstance(window, list) or len(window) != 2:
            raise ValueError(f"{at}: 'between' must be [\"HH:MM\", \"HH:MM\"]")
        start, end = parse_hhmm(window[0]), parse_hhmm(window[1])
        if start == end:
            raise ValueError(f"{at}: the window start and end must differ")
        if node.get("days") is not None:
            out["days"] = _str_list(node["days"], at, "days", allowed=DAYS, upper=True)
        if node.get("timezone") is not None:
            get_zone(node["timezone"])
    elif t == "watchlist":
        out["present"] = _bool(node.get("present"), at, "present", True)
        if node.get("status") is not None:
            out["status"] = _str_list(node["status"], at, "status", allowed=("alert", "review"))
        if node.get("risk_level_min") is not None:
            out["risk_level_min"] = _str_list(node["risk_level_min"], at, "risk_level_min",
                                              allowed=SEVERITIES, upper=True)[0]
        if node.get("entity_types") is not None:
            out["entity_types"] = _str_list(node["entity_types"], at, "entity_types",
                                            allowed=ENTITY_TYPES, upper=True)
    elif t == "plate":
        if "read" not in node and "authorized" not in node:
            raise ValueError(f"{at}: give 'read' and/or 'authorized'")
        for key in ("read", "authorized"):
            if key in node:
                out[key] = _bool(node[key], at, key, True)
    elif t == "track_age":
        out["min_s"] = _number(node.get("min_s"), at, "min_s", 0.0)
    elif t in ("all", "any"):
        subs = node.get("conditions")
        if not isinstance(subs, list) or not subs:
            raise ValueError(f"{at}: 'conditions' must be a non-empty list")
        out["conditions"] = [validate_condition(s, f"{where}.{t}[{i}]") for i, s in enumerate(subs)]
    elif t == "not":
        out["condition"] = validate_condition(node.get("condition"), f"{where}.not")
    return out


def walk_conditions(conditions: List[dict]) -> Iterator[dict]:
    """Every condition node, including those nested in all / any / not."""
    for c in conditions:
        yield c
        if c["type"] in ("all", "any"):
            yield from walk_conditions(c["conditions"])
        elif c["type"] == "not":
            yield from walk_conditions([c["condition"]])


# ----------------------------------------------------------------------------- the file
def parse_behaviour_config(data: dict, source: str = "<dict>") -> BehaviourConfig:
    if data.get("version", 1) != 1:
        raise ValueError(f"{source}: unsupported rules version {data.get('version')!r}")

    site = data.get("site", {}) or {}
    tz = site.get("timezone", "UTC")
    get_zone(tz)
    camera_tz = {}
    for cid, spec in (site.get("cameras") or {}).items():
        name = spec.get("timezone", tz) if isinstance(spec, dict) else None
        if name is None:
            raise ValueError(f"{source}: site.cameras.{cid} must be an object with a 'timezone'")
        get_zone(name)
        camera_tz[cid] = name

    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError(f"{source}: 'rules' must be a list")

    rules, seen = [], set()
    for i, r in enumerate(raw_rules, 1):
        rid = str(r.get("rule_id", "")).strip()
        where = f"{source} rule {rid or '#' + str(i)}"
        if not rid:
            raise ValueError(f"{where}: 'rule_id' is required")
        if rid in seen:
            raise ValueError(f"{where}: duplicate rule_id")
        seen.add(rid)

        name = str(r.get("name", "")).strip()
        if not name:
            raise ValueError(f"{where}: 'name' is required")
        etype = str(r.get("event_type", ""))
        if not EVENT_TYPE_RE.match(etype):
            raise ValueError(f"{where}: event_type must match {EVENT_TYPE_RE.pattern}")
        if etype in RESERVED_EVENT_TYPES:
            raise ValueError(f"{where}: event_type {etype!r} is an observation name; choose another")

        action = r.get("action") or {}
        severity = str(action.get("severity", "")).upper()
        if severity not in SEVERITIES:
            raise ValueError(f"{where}: action.severity must be one of {SEVERITIES}")
        points = _number(action.get("score"), where, "action.score", 0.0)
        if points > 100 or int(points) != points:
            raise ValueError(f"{where}: action.score must be a whole number from 0 to 100")

        conds = r.get("conditions")
        if not isinstance(conds, list) or not conds:
            raise ValueError(f"{where}: 'conditions' must be a non-empty list")
        conditions = [validate_condition(c, f"{where}.conditions[{j}]") for j, c in enumerate(conds)]

        cameras = r.get("cameras")
        if cameras is not None:
            cameras = _str_list(cameras, where, "cameras")

        rules.append(Rule(
            rule_id=rid, name=name, event_type=etype, conditions=conditions, severity=severity,
            points=int(points), enabled=_bool(r.get("enabled"), where, "enabled", True), cameras=cameras,
            cooldown_s=_number(r.get("cooldown_s"), where, "cooldown_s", 0.0, 0.0),
            rearm_s=_number(r.get("rearm_s"), where, "rearm_s", 0.0, 30.0),
            description=str(r.get("description", ""))))

    cfg = BehaviourConfig(tz, camera_tz, str(data.get("authorized_plates_csv", "") or ""), rules)
    for rule in rules:
        if rule.enabled and any(c["type"] == "plate" and "authorized" in c for c in walk_conditions(rule.conditions)):
            if not cfg.authorized_plates_csv:
                raise ValueError(f"{source} rule {rule.rule_id}: uses plate.authorized but "
                                 f"'authorized_plates_csv' is not set (every plate would count as unauthorized)")
    return cfg


def load_behaviour_config(path: Path) -> BehaviourConfig:
    with open(path, "r", encoding="utf-8") as f:
        return parse_behaviour_config(json.load(f), source=str(path))


def check_rules_against_zones(cfg: BehaviourConfig, zones_dir: Path) -> Tuple[List[str], List[str]]:
    """Compare the zone and line names used by the rules with the zone files (Day 6).
    Returns (errors, warnings). A rule restricted to named cameras must find its zones and lines on
    each of them; a rule for all cameras must find them on at least one."""
    from app.analytics.rules_config import load_camera_rules

    zone_ids, zone_types, line_ids = {}, {}, {}
    for path in sorted(Path(zones_dir).glob("*.json")):
        cr = load_camera_rules(path)
        zone_ids[cr.camera_id] = {z.id for z in cr.zones}
        zone_types[cr.camera_id] = {z.type for z in cr.zones}
        line_ids[cr.camera_id] = {ln.id for ln in cr.lines}

    errors: List[str] = []
    warnings: List[str] = []
    for rule in cfg.rules:
        if not rule.enabled:
            continue
        cams = rule.cameras if rule.cameras else list(zone_ids)
        for node in walk_conditions(rule.conditions):
            checks = []
            if node["type"] == "zone":
                if node.get("zone_id"):
                    checks.append(("zone", node["zone_id"], zone_ids))
                if node.get("zone_type") not in (None, "any"):
                    checks.append(("zone type", node["zone_type"], zone_types))
            elif node["type"] == "line_crossing" and node.get("line"):
                checks.append(("line", node["line"], line_ids))
            for label, wanted, table in checks:
                for cam in cams:
                    if cam not in table:
                        (errors if rule.cameras else warnings).append(
                            f"{rule.rule_id}: camera {cam} has no zones file in {zones_dir}")
                missing = [cam for cam in cams if cam in table and wanted not in table[cam]]
                if rule.cameras and missing:
                    errors.append(f"{rule.rule_id}: {label} {wanted!r} not defined on {missing}")
                elif not rule.cameras and cams and len(missing) == len([c for c in cams if c in table]):
                    errors.append(f"{rule.rule_id}: {label} {wanted!r} is not defined on any camera")
                elif missing:
                    warnings.append(f"{rule.rule_id}: {label} {wanted!r} is not defined on {missing}")
    return errors, warnings
