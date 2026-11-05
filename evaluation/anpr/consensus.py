"""Multi-frame consensus replay harness and early-stop benchmark (Mode M3).

Evaluates consensus voting strategies across vehicle tracks:
- S1: Best-confidence single frame (upper bound for single frame).
- S2: First valid (stop on first valid Indian format).
- S3: Majority string vote (unweighted mode).
- S4: Confidence-weighted string vote.
- S5: Positional character voting with confidence weighting (production).

Benchmarks early-stopping efficiency:
- OCR calls saved (% compute reduction).
- Decision latency.
- Accuracy delta vs unconstrained multi-frame budget.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Tuple

from evaluation.anpr.metrics import plate_key, plate_norm, score_pair
from evaluation.anpr.predict import validate_plate


@dataclass
class TrackFrameRead:
    """A single frame OCR emission along a vehicle track."""
    frame_index: int
    text: str
    confidence: float
    timestamp_ms: float = 0.0
    level: str = "loose"                       # strict, loose, invalid
    weight: float = 1.0

    @property
    def clean_text(self) -> str:
        return plate_norm(self.text)


@dataclass
class VehicleTrack:
    """Full chronological sequence of frames and GT for one vehicle."""
    vehicle_id: str
    gt_plate: str
    reads: List[TrackFrameRead]
    vehicle_type: str = "car"
    condition: str = "day"

    @property
    def total_frames(self) -> int:
        return len(self.reads)


@dataclass
class ConsensusDecision:
    """Decision output of a consensus strategy on a track."""
    vehicle_id: str
    predicted_plate: str
    strategy: str
    confidence: float
    frames_used: int
    total_frames: int
    stopped_early: bool
    latency_ms: float
    gt_plate: str

    @property
    def exact_match(self) -> bool:
        return plate_norm(self.predicted_plate) == plate_norm(self.gt_plate)

    @property
    def lookalike_match(self) -> bool:
        p = plate_norm(self.predicted_plate)
        g = plate_norm(self.gt_plate)
        return (p == g) or (bool(p) and bool(g) and plate_key(p) == plate_key(g))


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def strategy_best_confidence(reads: List[TrackFrameRead]) -> Tuple[str, float]:
    """S1: Best-confidence single frame."""
    if not reads:
        return "", 0.0
    best = max(reads, key=lambda r: r.confidence)
    return best.clean_text, best.confidence


def strategy_first_valid(reads: List[TrackFrameRead]) -> Tuple[str, float, int]:
    """S2: First valid Indian format read (returns text, conf, frames_consumed)."""
    if not reads:
        return "", 0.0, 0
    for idx, r in enumerate(reads):
        clean, valid = validate_plate(r.text, level="strict_state")
        if valid:
            return clean, r.confidence, idx + 1
    # Fallback to first read
    first = reads[0]
    return first.clean_text, first.confidence, 1


def strategy_majority_vote(reads: List[TrackFrameRead]) -> Tuple[str, float]:
    """S3: Majority string vote (unweighted)."""
    valid_texts = [r.clean_text for r in reads if r.clean_text]
    if not valid_texts:
        return "", 0.0
    counts = Counter(valid_texts)
    winner, top_cnt = counts.most_common(1)[0]
    share = top_cnt / len(valid_texts)
    confs = [r.confidence for r in reads if r.clean_text == winner]
    avg_conf = mean(confs) if confs else 0.5
    return winner, avg_conf * share


def strategy_confidence_weighted_vote(reads: List[TrackFrameRead]) -> Tuple[str, float]:
    """S4: Confidence-weighted string vote."""
    weights: Dict[str, float] = defaultdict(float)
    confs: Dict[str, List[float]] = defaultdict(list)
    for r in reads:
        t = r.clean_text
        if t:
            weights[t] += r.confidence
            confs[t].append(r.confidence)
    if not weights:
        return "", 0.0
    total = sum(weights.values()) or 1e-6
    winner = max(weights, key=weights.get)
    share = weights[winner] / total
    return winner, mean(confs[winner]) * share


def strategy_positional_consensus(reads: List[TrackFrameRead]) -> Tuple[str, float]:
    """S5: Positional character voting with confidence weighting (production)."""
    valid_reads = [r for r in reads if r.clean_text]
    if not valid_reads:
        return "", 0.0

    # 1. Exact string candidate
    str_winner, str_conf = strategy_confidence_weighted_vote(valid_reads)

    # 2. Length grouping for positional alignment
    len_weights: Dict[int, float] = defaultdict(float)
    for r in valid_reads:
        len_weights[len(r.clean_text)] += r.confidence
    dominant_len = max(len_weights, key=len_weights.get)

    grouped = [r for r in valid_reads if len(r.clean_text) == dominant_len]
    if len(grouped) >= 2 and len({r.clean_text for r in grouped}) > 1:
        chars = []
        agreements = []
        for i in range(dominant_len):
            pos_weights: Dict[str, float] = defaultdict(float)
            for r in grouped:
                pos_weights[r.clean_text[i]] += r.confidence
            total_pos = sum(pos_weights.values()) or 1e-6
            best_char = max(pos_weights, key=pos_weights.get)
            chars.append(best_char)
            agreements.append(pos_weights[best_char] / total_pos)

        assembled = "".join(chars)
        char_agree = mean(agreements) if agreements else 0.5

        # Check if assembled positional candidate is format-valid
        _, valid = validate_plate(assembled, level="strict")
        if valid and char_agree >= 0.60:
            avg_c = mean(r.confidence for r in grouped)
            return assembled, avg_c * char_agree

    return str_winner, str_conf


# ---------------------------------------------------------------------------
# Replay Runner & Early Stopping
# ---------------------------------------------------------------------------

@dataclass
class EarlyStopConfig:
    min_reads: int = 3
    stable_share: float = 0.60
    confidence_thresh: float = 0.85


def replay_track(
    track: VehicleTrack,
    strategy: str = "S5",
    frame_budget: Optional[int] = None,
    early_stop: Optional[EarlyStopConfig] = None,
) -> ConsensusDecision:
    """Replay track frames incrementally through the selected strategy."""
    available_reads = track.reads[:frame_budget] if frame_budget else track.reads
    if not available_reads:
        return ConsensusDecision(
            vehicle_id=track.vehicle_id,
            predicted_plate="",
            strategy=strategy,
            confidence=0.0,
            frames_used=0,
            total_frames=len(track.reads),
            stopped_early=False,
            latency_ms=0.0,
            gt_plate=track.gt_plate,
        )

    if early_stop is None or strategy == "S1":
        # Process all budgeted frames
        reads_to_use = available_reads
        stopped_early = False
        frames_consumed = len(reads_to_use)
    else:
        # Stream frame by frame
        reads_to_use = []
        stopped_early = False
        frames_consumed = 0
        for idx, r in enumerate(available_reads):
            reads_to_use.append(r)
            frames_consumed = idx + 1
            if len(reads_to_use) >= early_stop.min_reads:
                # Test stability
                text, conf = strategy_positional_consensus(reads_to_use)
                _, valid = validate_plate(text, level="strict")
                if valid and conf >= early_stop.confidence_thresh:
                    stopped_early = True
                    break

    # Compute prediction with chosen strategy
    if strategy == "S1":
        text, conf = strategy_best_confidence(reads_to_use)
    elif strategy == "S2":
        text, conf, frames_consumed = strategy_first_valid(reads_to_use)
        stopped_early = frames_consumed < len(available_reads)
    elif strategy == "S3":
        text, conf = strategy_majority_vote(reads_to_use)
    elif strategy == "S4":
        text, conf = strategy_confidence_weighted_vote(reads_to_use)
    elif strategy == "S5":
        text, conf = strategy_positional_consensus(reads_to_use)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    latency_ms = reads_to_use[frames_consumed - 1].timestamp_ms if frames_consumed > 0 else 0.0

    return ConsensusDecision(
        vehicle_id=track.vehicle_id,
        predicted_plate=text,
        strategy=strategy,
        confidence=conf,
        frames_used=frames_consumed,
        total_frames=len(track.reads),
        stopped_early=stopped_early,
        latency_ms=latency_ms,
        gt_plate=track.gt_plate,
    )


@dataclass
class StrategyBenchmarkResult:
    strategy: str
    total_tracks: int
    exact_accuracy: float
    lookalike_accuracy: float
    avg_frames_used: float
    pct_calls_saved: float
    avg_latency_ms: float


def benchmark_strategies(
    tracks: List[VehicleTrack],
    early_stop: Optional[EarlyStopConfig] = None,
) -> List[StrategyBenchmarkResult]:
    """Compare all 5 strategies on the tracks."""
    strategies = ["S1", "S2", "S3", "S4", "S5"]
    results = []
    total_available_calls = sum(len(t.reads) for t in tracks) or 1

    for strat in strategies:
        decisions = [replay_track(t, strategy=strat, early_stop=early_stop) for t in tracks]
        exact_cnt = sum(d.exact_match for d in decisions)
        look_cnt = sum(d.lookalike_match for d in decisions)
        calls_used = sum(d.frames_used for d in decisions)
        latencies = [d.latency_ms for d in decisions if d.latency_ms > 0.0]

        pct_saved = max(0.0, (total_available_calls - calls_used) / total_available_calls)

        results.append(
            StrategyBenchmarkResult(
                strategy=strat,
                total_tracks=len(tracks),
                exact_accuracy=exact_cnt / len(tracks) if tracks else 0.0,
                lookalike_accuracy=look_cnt / len(tracks) if tracks else 0.0,
                avg_frames_used=calls_used / len(tracks) if tracks else 0.0,
                pct_calls_saved=pct_saved,
                avg_latency_ms=mean(latencies) if latencies else 0.0,
            )
        )
    return results


def evaluate_accuracy_vs_frames(
    tracks: List[VehicleTrack],
    budgets: Tuple[int, ...] = (1, 2, 3, 5, 8, 10),
    strategy: str = "S5",
) -> List[Tuple[int, float]]:
    """Evaluates consensus exact accuracy as a function of maximum allowed frames."""
    curve = []
    for b in budgets:
        decisions = [replay_track(t, strategy=strategy, frame_budget=b, early_stop=None) for t in tracks]
        acc = sum(d.exact_match for d in decisions) / len(tracks) if tracks else 0.0
        curve.append((b, acc))
    return curve
