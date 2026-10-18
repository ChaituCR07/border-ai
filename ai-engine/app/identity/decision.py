from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from app.identity.config import FaceConfig


def similarity_score(similarity: float, review_threshold: float) -> int:
    """A 0-100 ranking score: the review threshold maps to 50 and a perfect match to 100.
    It is NOT a probability; it exists so later stages (threat scoring) can rank matches."""
    span = max(1.0 - review_threshold, 1e-6)
    return int(round(max(0.0, min(100.0, 50.0 + 50.0 * (similarity - review_threshold) / span))))


@dataclass
class FaceDecision:
    status: Optional[str]            # 'review' | 'alert' | None
    reason: str                      # 'ok' or why there is no match
    score: int = 0
    entry: Any = None
    similarity: float = 0.0
    margin: float = 0.0


def decide_face_match(results: List[Tuple[Any, float]], n_embeddings: int, consistency: float,
                      cfg: FaceConfig) -> FaceDecision:
    """results: [(watchlist entry, cosine similarity), ...] best first."""
    if not results:
        return FaceDecision(None, "empty_gallery")
    if n_embeddings < cfg.min_embeddings:
        return FaceDecision(None, "too_few_embeddings")
    if consistency < cfg.min_consistency:
        return FaceDecision(None, "inconsistent")
    entry, best = results[0]
    if best < cfg.review_threshold:
        return FaceDecision(None, "below_threshold", similarity=best)
    margin = best - results[1][1] if len(results) > 1 else 1.0
    if margin < cfg.min_margin:
        return FaceDecision(None, "ambiguous", similarity=best, margin=margin)
    status = "alert" if (cfg.allow_alert and best >= cfg.alert_threshold) else "review"
    return FaceDecision(status, "ok", similarity_score(best, cfg.review_threshold), entry, best, margin)
