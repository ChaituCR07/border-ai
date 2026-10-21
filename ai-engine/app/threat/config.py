import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

LEVEL_NAMES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
LEVEL_RANK = {name: i for i, name in enumerate(LEVEL_NAMES)}
SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
EVENT_FIELDS = {"rule_id", "rule_type", "rule_kind", "direction", "object_class", "camera_id"}
TOP_KEYS = {"max_score", "window_s", "alert_min_score", "cooldown_s", "rearm_s", "merge_by_plate",
            "merge_scope", "levels", "bonus", "sources"}


@dataclass
class Source:
    id: str
    label: str
    event_type: str
    points: Union[int, str]                              # a whole number, or "from_event"
    where: Dict[str, object] = field(default_factory=dict)
    status_multiplier: Dict[str, float] = field(default_factory=dict)
    max_occurrences: int = 1
    excluded_by: List[str] = field(default_factory=list)


@dataclass
class Bonus:
    points: int
    min_distinct_kinds: int


@dataclass
class ScoringConfig:
    max_score: int
    window_s: float
    alert_min_score: int
    cooldown_s: float
    rearm_s: float
    merge_by_plate: bool
    merge_scope: str
    levels: List[Tuple[str, int]]                        # (name, minimum score), ascending
    bonus: Optional[Bonus]
    sources: List[Source]

    def level_for(self, score: int) -> str:
        level = self.levels[0][0]
        for name, minimum in self.levels:
            if score >= minimum:
                level = name
        return level

    def source(self, source_id: str) -> Source:
        for s in self.sources:
            if s.id == source_id:
                return s
        raise ValueError(f"unknown scoring source {source_id!r}")


# ----------------------------------------------------------------------------- matching
def get_field(event, path: str):
    """An event attribute (`rule_type`) or a details entry (`details.entity_type`); None if absent."""
    if path.startswith("details."):
        cur = event.details
        for part in path[len("details."):].split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur
    return getattr(event, path, None)


def source_matches(src: Source, event) -> bool:
    if event.type != src.event_type:
        return False
    for path, expected in src.where.items():
        actual = get_field(event, path)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True

import json
from pathlib import Path
from app.behaviour.rules_config import _bool, _number, _str_list


# ----------------------------------------------------------------------------- parsing
def _parse_source(raw: dict, where: str) -> Source:
    allowed = {"id", "label", "match", "points", "status_multiplier", "max_occurrences", "excluded_by"}
    extra = set(raw) - allowed
    if extra:
        raise ValueError(f"{where}: unknown keys {sorted(extra)}")
    sid = str(raw.get("id", ""))
    if not SOURCE_ID_RE.match(sid) or sid == "multiple_suspicious":
        raise ValueError(f"{where}: 'id' must be lower case letters, digits, and underscores "
                         f"(and not 'multiple_suspicious')")
    where = f"{where} ({sid})"
    label = str(raw.get("label", "")).strip()
    if not label:
        raise ValueError(f"{where}: 'label' is required")

    match = raw.get("match")
    if not isinstance(match, dict) or set(match) - {"event_type", "where"}:
        raise ValueError(f"{where}: 'match' must contain 'event_type' and optionally 'where'")
    etype = str(match.get("event_type", "")).strip().upper()
    if not etype:
        raise ValueError(f"{where}: match.event_type is required")
    conds = match.get("where", {}) or {}
    if not isinstance(conds, dict):
        raise ValueError(f"{where}: match.where must be an object")
    for key, value in conds.items():
        if not (key.startswith("details.") or key in EVENT_FIELDS):
            raise ValueError(f"{where}: match.where key {key!r} must be one of {sorted(EVENT_FIELDS)} "
                             f"or start with 'details.'")
        values = value if isinstance(value, list) else [value]
        if not values or not all(isinstance(v, (str, int, float, bool)) for v in values):
            raise ValueError(f"{where}: match.where[{key!r}] must be a simple value or a list of them")

    points = raw.get("points")
    if points != "from_event":
        points = _number(points, where, "points", 0.0)
        if points > 100 or int(points) != points:
            raise ValueError(f"{where}: 'points' must be a whole number from 0 to 100, or \"from_event\"")
        points = int(points)

    mult = raw.get("status_multiplier") or {}
    if not isinstance(mult, dict) or set(mult) - {"alert", "review"}:
        raise ValueError(f"{where}: status_multiplier keys must be 'alert' and/or 'review'")
    mult = {k: _number(v, where, f"status_multiplier.{k}", 0.0) for k, v in mult.items()}
    if any(v > 1.0 for v in mult.values()):
        raise ValueError(f"{where}: status_multiplier values must be between 0 and 1")

    occurrences = _number(raw.get("max_occurrences"), where, "max_occurrences", 1.0, 1.0)
    if int(occurrences) != occurrences:
        raise ValueError(f"{where}: 'max_occurrences' must be a whole number")
    excluded = _str_list(raw["excluded_by"], where, "excluded_by") if raw.get("excluded_by") else []
    return Source(sid, label, etype, points, conds, mult, int(occurrences), excluded)


def parse_scoring_config(data: dict, source: str = "<dict>") -> ScoringConfig:
    s = data.get("scoring")
    if not isinstance(s, dict):
        raise ValueError(f"{source}: there is no 'scoring' section")
    extra = set(s) - TOP_KEYS
    if extra:
        raise ValueError(f"{source}: unknown scoring keys {sorted(extra)}")

    max_score = int(_number(s.get("max_score"), source, "max_score", 1.0, 100.0))
    window_s = _number(s.get("window_s"), source, "window_s", 1.0, 600.0)
    alert_min = int(_number(s.get("alert_min_score"), source, "alert_min_score", 0.0, 10.0))
    if alert_min > max_score:
        raise ValueError(f"{source}: alert_min_score cannot exceed max_score")
    scope = s.get("merge_scope", "camera")
    if scope not in ("camera", "global"):
        raise ValueError(f"{source}: merge_scope must be 'camera' or 'global'")

    raw_levels = s.get("levels")
    if not isinstance(raw_levels, list) or [lv.get("name") for lv in raw_levels] != list(LEVEL_NAMES):
        raise ValueError(f"{source}: 'levels' must list exactly {list(LEVEL_NAMES)} in that order")
    levels, previous = [], -1
    for lv in raw_levels:
        minimum = int(_number(lv.get("min"), source, f"levels.{lv['name']}.min", 0.0))
        if not levels and minimum != 0:
            raise ValueError(f"{source}: the first level must start at 0")
        if minimum <= previous:
            raise ValueError(f"{source}: level minimums must increase")
        if minimum > max_score:
            raise ValueError(f"{source}: a level minimum exceeds max_score")
        levels.append((lv["name"], minimum))
        previous = minimum

    bonus = None
    raw_bonus = (s.get("bonus") or {}).get("multiple_suspicious")
    if raw_bonus:
        bonus = Bonus(int(_number(raw_bonus.get("points"), source, "bonus.points", 0.0, 10.0)),
                      int(_number(raw_bonus.get("min_distinct_kinds"), source, "bonus.min_distinct_kinds", 1.0, 4.0)))

    raw_sources = s.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError(f"{source}: 'sources' must be a non-empty list")
    sources = [_parse_source(r, f"{source} sources[{i}]") for i, r in enumerate(raw_sources)]
    ids = [src.id for src in sources]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{source}: duplicate source id")
    for src in sources:
        for ex in src.excluded_by:
            if ex not in ids:
                raise ValueError(f"{source}: source {src.id!r} is excluded_by unknown source {ex!r}")
            if ex == src.id or src.id in next(x for x in sources if x.id == ex).excluded_by:
                raise ValueError(f"{source}: sources {src.id!r} and {ex!r} exclude each other")

    return ScoringConfig(max_score, window_s, alert_min, _number(s.get("cooldown_s"), source, "cooldown_s", 0.0, 60.0),
                         _number(s.get("rearm_s"), source, "rearm_s", 0.0, 300.0),
                         _bool(s.get("merge_by_plate"), source, "merge_by_plate", True), scope,
                         levels, bonus, sources)


def load_scoring_config(path: Path) -> ScoringConfig:
    with open(path, "r", encoding="utf-8") as f:
        return parse_scoring_config(json.load(f), source=str(path))


def check_scoring_against_rules(scoring: ScoringConfig, behaviour) -> List[str]:
    """Warnings about scoring sources and behaviour rules that do not line up."""
    warnings: List[str] = []
    produced = {r.event_type for r in behaviour.rules if r.enabled}
    scored = {s.event_type for s in scoring.sources}
    for s in scoring.sources:
        if s.points == "from_event" and s.event_type not in produced:
            warnings.append(f"scoring source '{s.id}' counts {s.event_type}, but no enabled rule produces it")
    for r in behaviour.rules:
        if r.enabled and r.event_type not in scored:
            warnings.append(f"rule {r.rule_id} produces {r.event_type}, but no scoring source counts it "
                            f"(its {r.points} points are ignored)")
    return warnings
