from typing import Dict, List

from app.threat.config import ScoringConfig
from app.threat.scoring import total_score


def evaluate_items(scoring: ScoringConfig, behaviour_points: Dict[str, int], items: List[str]) -> dict:
    """items look like 'zone_violation' or 'watchlist_vehicle:review' (kind[:status])."""
    kind_points: Dict[str, int] = {}
    rows = []
    for item in items:
        kind, _, status = item.partition(":")
        src = scoring.source(kind)
        points = src.points if isinstance(src.points, int) else behaviour_points.get(src.event_type)
        if points is None:
            raise ValueError(f"no points known for '{kind}': no behaviour rule produces {src.event_type}")
        if src.status_multiplier:
            points = int(round(points * src.status_multiplier.get(status or "alert", 1.0)))
        kind_points[kind] = max(kind_points.get(kind, 0), points)
        rows.append((kind, src.label, points))
    result = total_score(kind_points, scoring)
    return {"rows": rows, "result": result, "level": scoring.level_for(result.score)}
