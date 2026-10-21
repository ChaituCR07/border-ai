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
