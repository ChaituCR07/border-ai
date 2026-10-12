from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Callable, List, Optional, Tuple

import numpy as np

from app.anpr.plate_format import LEVEL_RANK
from app.anpr.types import PlateRead


@dataclass
class ConsensusResult:
    text: str
    confidence: float        # heuristic: mean OCR confidence of supporting reads x agreement
    votes: int               # reads that exactly match the chosen text
    n_reads: int
    agreement: float         # weighted share (exact vote) or mean per-position agreement (char vote)
    level: str               # strict | loose | invalid
    method: str              # exact | char


class PlateConsensus:
    """Accumulates the reads for ONE vehicle and decides the plate.
    normalize(text) -> (corrected_text, level) is used to validate character-vote candidates."""

    def __init__(self, normalize: Callable[[str], Tuple[str, str]],
                 min_reads: int = 3, stable_share: float = 0.6):
        self.normalize = normalize
        self.min_reads = min_reads
        self.stable_share = stable_share
        self.reads: List[PlateRead] = []

    def add(self, read: PlateRead) -> None:
        self.reads.append(read)

    @property
    def n_reads(self) -> int:
        return len(self.reads)

    def best_crop(self) -> Optional[np.ndarray]:
        crops = [r for r in self.reads if r.crop is not None]
        return max(crops, key=lambda r: r.weight).crop if crops else None

    def best(self) -> Optional[ConsensusResult]:
        if not self.reads:
            return None
        n = len(self.reads)
        total = sum(r.weight for r in self.reads) or 1e-9

        # 1) exact-string vote
        weight, confs, level_of = defaultdict(float), defaultdict(list), {}
        counts = defaultdict(int)
        for r in self.reads:
            weight[r.text] += r.weight
            confs[r.text].append(r.confidence)
            counts[r.text] += 1
            level_of[r.text] = r.level
        top = max(weight, key=weight.get)
        share = weight[top] / total
        exact = ConsensusResult(top, mean(confs[top]) * share, counts[top], n, share,
                                level_of[top], "exact")

        # 2) character vote over the dominant length
        by_len = defaultdict(float)
        for r in self.reads:
            by_len[len(r.text)] += r.weight
        length = max(by_len, key=by_len.get)
        group = [r for r in self.reads if len(r.text) == length]
        if len(group) >= 2 and len({r.text for r in group}) > 1:
            chars, agree = [], []
            for i in range(length):
                pos = defaultdict(float)
                for r in group:
                    pos[r.text[i]] += r.weight
                ch = max(pos, key=pos.get)
                chars.append(ch)
                agree.append(pos[ch] / sum(pos.values()))
            text, level = self.normalize("".join(chars))
            if text != top and (share < 0.5 or LEVEL_RANK[level] > LEVEL_RANK[exact.level]):
                char_agreement = mean(agree)
                return ConsensusResult(
                    text, mean(r.confidence for r in group) * char_agreement,
                    sum(1 for r in group if r.text == text), n, char_agreement, level, "char")
        return exact

    def is_stable(self, result: Optional[ConsensusResult] = None) -> bool:
        """Stable = enough reads, enough agreement, and a text that fits a known format."""
        result = result or self.best()
        return bool(result and result.n_reads >= self.min_reads
                    and result.agreement >= self.stable_share
                    and result.level != "invalid")
