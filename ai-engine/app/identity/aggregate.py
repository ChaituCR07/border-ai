from typing import List, Optional, Tuple

import numpy as np

from app.identity.embeddings import l2_normalize


class EmbeddingAggregator:
    def __init__(self, max_items: int = 15):
        self.max_items = max_items
        self.items: List[Tuple[np.ndarray, float, float]] = []       # (embedding, quality, timestamp)

    def add(self, embedding, quality: float, timestamp: float) -> None:
        self.items.append((l2_normalize(embedding), max(float(quality), 1e-3), float(timestamp)))
        if len(self.items) > self.max_items:                          # keep the best ones
            worst = min(range(len(self.items)), key=lambda i: self.items[i][1])
            self.items.pop(worst)

    def __len__(self) -> int:
        return len(self.items)

    def aggregate(self) -> Optional[np.ndarray]:
        """Quality-weighted mean, L2-normalized."""
        if not self.items:
            return None
        weights = np.array([q for _, q, _ in self.items], dtype=np.float32)
        stacked = np.stack([e for e, _, _ in self.items])
        return l2_normalize((stacked * weights[:, None]).sum(axis=0))

    def consistency(self) -> float:
        """Mean cosine similarity of each embedding to the aggregate (1.0 for a single item).
        Low values mean mixed identities or poor, noisy embeddings."""
        agg = self.aggregate()
        if agg is None or len(self.items) == 1:
            return 1.0
        return float(np.mean([float(np.dot(e, agg)) for e, _, _ in self.items]))

    def quality_mean(self) -> float:
        return float(np.mean([q for _, q, _ in self.items])) if self.items else 0.0
