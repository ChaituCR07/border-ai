from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from app.anpr.plate_format import DIGIT_TO_LETTER, LETTER_TO_DIGIT
from app.watchlist.config import WatchlistConfig
from app.watchlist.models import RISK_RANK, WatchlistEntry

# Characters OCR commonly confuses (same table the plate correction in ANPR uses)
CONFUSABLE = ({frozenset((d, l)) for d, l in DIGIT_TO_LETTER.items()}
              | {frozenset((l, d)) for l, d in LETTER_TO_DIGIT.items()})


def ocr_distance(a: str, b: str) -> Optional[float]:
    """Substitution-only distance. Look-alike swaps cost 0.5, any other substitution 1.0.
    Strings of different lengths are never near matches (returns None)."""
    if len(a) != len(b):
        return None
    total = 0.0
    for x, y in zip(a, b):
        if x != y:
            total += 0.5 if frozenset((x, y)) in CONFUSABLE else 1.0
    return total


@dataclass
class Match:
    entry: WatchlistEntry
    match_type: str                       # exact | near
    distance: float
    quality: float                        # 1.0 for exact; 1 - near_penalty x distance for near
    also: List[int] = field(default_factory=list)      # other entries that matched exactly


def find_best(plate: str, exact_entries: Sequence[WatchlistEntry],
              near_candidates: Sequence[WatchlistEntry], cfg: WatchlistConfig) -> Optional[Match]:
    """Best match for a normalized plate: an exact match wins (highest risk first);
    otherwise the closest near match within the allowed distance."""
    if exact_entries:
        ranked = sorted(exact_entries, key=lambda e: (-RISK_RANK[e.risk_level], e.watchlist_id))
        return Match(ranked[0], "exact", 0.0, 1.0, [e.watchlist_id for e in ranked[1:]])
    if cfg.near_max_distance <= 0:
        return None

    best = None
    for e in near_candidates:
        d = ocr_distance(plate, e.normalized_identifier)
        if d is None or d == 0 or d > cfg.near_max_distance:
            continue
        key = (d, -RISK_RANK[e.risk_level], e.watchlist_id)
        if best is None or key < best[0]:
            best = (key, e, d)
    if best is None:
        return None
    _, entry, d = best
    return Match(entry, "near", d, max(0.0, 1.0 - cfg.near_penalty * d))


def lookup_in_repo(repo, plate: str, cfg: WatchlistConfig) -> Optional[Match]:
    """The PostgreSQL lookup of your plan: an indexed exact query, then same-length candidates."""
    exact = repo.find_exact(plate, cfg.entity_types)
    near = [] if exact or cfg.near_max_distance <= 0 else repo.find_same_length(
        plate, cfg.entity_types, cfg.max_candidates)
    return find_best(plate, exact, near, cfg)


def lookup_in_snapshot(snapshot: Sequence[WatchlistEntry], plate: str, cfg: WatchlistConfig) -> Optional[Match]:
    """The same decision from an in-memory copy (used when the database is unreachable)."""
    exact = [e for e in snapshot if e.normalized_identifier == plate]
    near = [] if exact or cfg.near_max_distance <= 0 else [
        e for e in snapshot if len(e.normalized_identifier) == len(plate)]
    return find_best(plate, exact, near, cfg)


def score_for(plate_confidence: float, quality: float) -> int:
    """0-100. An exact match of a plate read at 0.91 confidence scores 91 (your plan's example)."""
    return int(round(max(0.0, min(1.0, plate_confidence)) * quality * 100))


def decide_status(match: Match, plate_confidence: float, score: int, cfg: WatchlistConfig) -> Optional[str]:
    """'alert', 'review', or None (too weak to record)."""
    if score < cfg.min_score:
        return None
    confident = plate_confidence >= cfg.alert_min_confidence
    if match.match_type == "exact":
        return "alert" if confident else "review"
    return "alert" if (cfg.near_can_alert and confident) else "review"
