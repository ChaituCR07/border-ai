from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from app.identity.aggregate import EmbeddingAggregator
from app.identity.config import FaceConfig
from app.identity.face import face_quality
from app.watchlist.models import InvalidEntry, WatchlistEntry, WatchlistError


class ConsentRequired(WatchlistError):
    """Enrollment was attempted without the explicit consent confirmation."""


@dataclass
class Enrollment:
    entry: WatchlistEntry
    used: int
    skipped: List[str]
    consistency: float


def enroll_subject(repo, engine, images: Sequence[np.ndarray], identifier: str, name: str, risk_level: str,
                   face_cfg: FaceConfig, *, consent_confirmed: bool, actor: str = "cli",
                   entity_type: str = "FACE", description: str = "", min_images: int = 3,
                   min_consistency: float = 0.75) -> Enrollment:
    """Create a face watchlist entry from several photos of ONE consenting person.
    Only the combined embedding is stored; the photos are not."""
    if not consent_confirmed:
        raise ConsentRequired("enrollment needs explicit confirmation that the person consented")

    agg, skipped = EmbeddingAggregator(max_items=max(len(images), 1)), []
    for idx, img in enumerate(images):
        faces = engine.detect(img)
        if not faces:
            skipped.append(f"image {idx}: no face")
            continue
        q = face_quality(img, faces[0], face_cfg)
        if not q.ok:
            skipped.append(f"image {idx}: {q.reason}")
            continue
        agg.add(engine.embed(img, faces[0]), q.score, 0.0)

    if len(agg) < min_images:
        raise InvalidEntry(f"only {len(agg)} usable photos, need at least {min_images} ({skipped})")
    consistency = agg.consistency()
    if consistency < min_consistency:
        raise InvalidEntry(f"the photos disagree with each other (consistency {consistency:.2f} < "
                           f"{min_consistency}): mixed people or poor photos")
    entry = repo.add_face(entity_type, identifier, name, risk_level, agg.aggregate(), engine.model_name,
                          count=len(agg), description=description, actor=actor)
    return Enrollment(entry, len(agg), skipped, consistency)
