import math
from statistics import mean, median
from typing import Dict, List, Tuple

from app.tracking.track_store import Track


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def find_fragment_candidates(tracks: List[Track], max_gap_s: float = 2.0,
                             max_dist_px: float = 150.0) -> List[Tuple[int, int]]:
    """Pairs (a, b) where track a ended and a track b of the same class began
    shortly after, nearby. Likely the same object that received a NEW ID, which
    is the signature of a fragmentation or an ID switch."""
    pairs = []
    for a in tracks:
        for b in tracks:
            if a is b or a.dominant_class != b.dominant_class:
                continue
            gap = b.first_seen - a.last_seen
            if 0 <= gap <= max_gap_s and _dist(a.last_point, b.first_point) <= max_dist_px:
                pairs.append((a.track_id, b.track_id))
    return pairs


def summarize_tracks(tracks: List[Track], short_s: float = 1.0) -> Dict:
    if not tracks:
        return {"tracks": 0, "short_tracks": 0, "mean_duration_s": 0.0,
                "median_duration_s": 0.0, "longest_s": 0.0, "fragment_candidates": 0}
    durations = [t.duration_s for t in tracks]
    return {
        "tracks": len(tracks),
        "short_tracks": sum(d < short_s for d in durations),
        "mean_duration_s": round(mean(durations), 2),
        "median_duration_s": round(median(durations), 2),
        "longest_s": round(max(durations), 2),
        "fragment_candidates": len(find_fragment_candidates(tracks)),
    }
