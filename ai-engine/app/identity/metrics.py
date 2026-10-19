import itertools
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def pair_similarities(embeddings_by_person: Dict[str, Sequence[np.ndarray]]) -> Tuple[List[float], List[float]]:
    """Cosine similarity of every same-person pair (genuine) and every different-person pair (impostor)."""
    genuine, impostor = [], []
    people = {p: np.stack(v) for p, v in embeddings_by_person.items() if len(v) > 0}
    for emb in people.values():
        sims = emb @ emb.T
        genuine += [float(sims[i, j]) for i, j in itertools.combinations(range(len(emb)), 2)]
    for a, b in itertools.combinations(people, 2):
        impostor += (people[a] @ people[b].T).flatten().astype(float).tolist()
    return genuine, impostor


def threshold_table(genuine: Sequence[float], impostor: Sequence[float], thresholds: Sequence[float]):
    """[(threshold, TAR, FAR)]: share of genuine pairs and of impostor pairs at or above the threshold."""
    g, i = np.asarray(genuine), np.asarray(impostor)
    return [(float(t), float((g >= t).mean()) if g.size else 0.0, float((i >= t).mean()) if i.size else 0.0)
            for t in thresholds]


def equal_error_rate(genuine: Sequence[float], impostor: Sequence[float]) -> Tuple[float, float]:
    """(EER, threshold) where the miss rate and the false-match rate are closest."""
    g, i = np.asarray(genuine), np.asarray(impostor)
    best = (1.0, 0.0, 1.0)
    for t in np.unique(np.concatenate([g, i])):
        frr, far = float((g < t).mean()), float((i >= t).mean())
        gap = abs(frr - far)
        if gap < best[2]:
            best = ((frr + far) / 2.0, float(t), gap)
    return best[0], best[1]


def threshold_for_far(genuine: Sequence[float], impostor: Sequence[float], target_far: float) -> Optional[float]:
    """Smallest threshold whose false-match rate (impostor similarity >= threshold) is at or below
    target_far. With few impostor pairs the resolution is limited: a measured FAR of 0 means
    'below 1 / number of impostor pairs', not 'zero'."""
    i = np.sort(np.asarray(impostor, dtype=float))
    if i.size == 0:
        return None
    for t in np.unique(i):
        if float((i > t).mean()) <= target_far:
            return float(np.nextafter(t, np.inf))        # just above t, so nothing equal to t counts
    return float(np.nextafter(i.max(), np.inf))


def expected_false_matches(far: float, gallery_size: int, strangers: int) -> float:
    """Expected strangers falsely matched to at least one enrolled face."""
    return strangers * (1.0 - (1.0 - far) ** gallery_size)


def rank_k_accuracy(queries: Sequence[Tuple[str, np.ndarray]], gallery: Sequence[Tuple[str, np.ndarray]],
                    ks=(1, 5)) -> Dict[int, float]:
    """Share of queries whose true person appears among the k most similar gallery items."""
    if not queries or not gallery:
        return {k: 0.0 for k in ks}
    ids = [g[0] for g in gallery]
    mat = np.stack([g[1] for g in gallery])
    hits = {k: 0 for k in ks}
    counted = 0
    for person, emb in queries:
        if person not in ids:
            continue
        counted += 1
        order = np.argsort(-(mat @ emb))
        for k in ks:
            if person in [ids[j] for j in order[:k]]:
                hits[k] += 1
    return {k: (hits[k] / counted if counted else 0.0) for k in ks}
