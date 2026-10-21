from dataclasses import dataclass, field
from typing import Dict, List

from app.threat.config import ScoringConfig


@dataclass
class ScoreResult:
    score: int                                    # after the cap
    raw: int                                      # before the cap (includes the bonus)
    bonus: int
    capped: bool
    counted: Dict[str, int] = field(default_factory=dict)       # kind -> points that count
    excluded: List[str] = field(default_factory=list)           # kinds present but not counted (double counting)


def total_score(kind_points: Dict[str, int], cfg: ScoringConfig) -> ScoreResult:
    """kind_points: points per kind after `max_occurrences` has been applied.
    Applies exclusions, the 'multiple suspicious' bonus, and the cap."""
    sources = {s.id: s for s in cfg.sources}
    present = {k for k, p in kind_points.items() if p > 0}
    counted: Dict[str, int] = {}
    excluded: List[str] = []
    for kind, points in kind_points.items():
        if points <= 0:
            continue
        src = sources.get(kind)
        if src is not None and any(x in present for x in src.excluded_by):
            excluded.append(kind)
            continue
        counted[kind] = points
    raw = sum(counted.values())
    bonus = cfg.bonus.points if cfg.bonus and len(counted) >= cfg.bonus.min_distinct_kinds else 0
    raw += bonus
    return ScoreResult(min(raw, cfg.max_score), raw, bonus, raw > cfg.max_score, counted, sorted(excluded))
