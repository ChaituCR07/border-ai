import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.identity.embeddings import l2_normalize
from app.watchlist.models import RepoUnavailable


class FaceGallery:
    """In-memory matrix of the enrolled face embeddings for ONE embedding model.
    Refreshed from the repository; if the database is unreachable the previous matrix is kept."""

    def __init__(self, repo, model_name: str, refresh_s: float = 60.0):
        self.repo, self.model_name, self.refresh_s = repo, model_name, refresh_s
        self._lock = threading.RLock()
        self._entries: list = []
        self._matrix = np.zeros((0, 0), np.float32)
        self._loaded_at = 0.0

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def reload(self) -> bool:
        try:
            pairs = self.repo.load_face_embeddings(self.model_name)
        except RepoUnavailable:
            return False
        with self._lock:
            self._entries = [e for e, _ in pairs]
            self._matrix = (np.stack([l2_normalize(v) for _, v in pairs]) if pairs
                            else np.zeros((0, 0), np.float32))
            self._loaded_at = time.time()
        return True

    def maybe_reload(self) -> None:
        if time.time() - self._loaded_at >= self.refresh_s:
            self.reload()

    def search(self, query, top_k: int = 2) -> List[Tuple[object, float]]:
        q = l2_normalize(query)
        with self._lock:
            if len(self._entries) == 0:
                return []
            if self._matrix.shape[1] != q.size:
                raise ValueError("query and gallery embeddings have different sizes (model mismatch)")
            sims = self._matrix @ q
            order = np.argsort(-sims)[:top_k]
            return [(self._entries[i], float(sims[i])) for i in order]


@dataclass
class ReidItem:
    camera_id: str
    track_id: int
    embedding: np.ndarray
    first_seen: float
    last_seen: float
    samples: int


@dataclass
class ReidCandidate:
    camera_id: str
    track_id: int
    similarity: float
    gap_s: float                      # time between that track's last sighting and this one's first (negative = overlap)


class ReidGallery:
    """Short-lived memory of recently finished person tracks, for cross-camera comparison.
    Holds embeddings only (no images), and forgets them after `ttl_s`."""

    def __init__(self, ttl_s: float = 900.0, max_items: int = 2000, max_gap_s: float = 600.0,
                 allow_overlap: bool = True, camera_pairs: Sequence[Sequence[str]] = ()):
        self.ttl_s, self.max_items, self.max_gap_s = ttl_s, max_items, max_gap_s
        self.allow_overlap = allow_overlap
        self.pairs = {frozenset(p) for p in camera_pairs}
        self._lock = threading.RLock()
        self._items: List[ReidItem] = []

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def add(self, item: ReidItem) -> None:
        with self._lock:
            self._items.append(item)
            if len(self._items) > self.max_items:
                self._items.pop(0)

    def prune(self, now: float) -> None:
        with self._lock:
            self._items = [i for i in self._items if now - i.last_seen <= self.ttl_s]

    def search(self, embedding, camera_id: str, first_seen: float, top_k: int = 3) -> List[ReidCandidate]:
        q = l2_normalize(embedding)
        with self._lock:
            items = list(self._items)
        eligible = []
        for it in items:
            if it.camera_id == camera_id:
                continue
            if self.pairs and frozenset((camera_id, it.camera_id)) not in self.pairs:
                continue
            gap = first_seen - it.last_seen
            if gap > self.max_gap_s or (gap < 0 and not self.allow_overlap):
                continue
            eligible.append((it, gap))
        if not eligible:
            return []
        sims = np.array([float(np.dot(q, it.embedding)) for it, _ in eligible])
        order = np.argsort(-sims)[:top_k]
        return [ReidCandidate(eligible[i][0].camera_id, eligible[i][0].track_id,
                              float(sims[i]), float(eligible[i][1])) for i in order]
