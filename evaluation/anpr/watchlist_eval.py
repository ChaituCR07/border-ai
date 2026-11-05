"""Watchlist collision simulation and false alert rate modeling (ADR 0023 / ADR 0039).

Simulates collision probabilities between benign traffic and watchlists of size
W in {10, 100, 1,000, 10,000} under both:
1. Exact matching (pred == watchlist)
2. Look-alike matching (plate_key(pred) == plate_key(watchlist))

Translates collision probabilities into expected false alerts per camera-day across traffic tiers:
- Low: 1,000 vehicles / day
- Medium: 10,000 vehicles / day
- High: 50,000 vehicles / day
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Set, Tuple

from evaluation.anpr.metrics import plate_key, plate_norm

TRAFFIC_TIERS = {
    "low": 1_000,
    "medium": 10_000,
    "high": 50_000,
}


@dataclass
class WatchlistTierMetrics:
    """Collision and false alert metrics for a specific watchlist size."""
    watchlist_size: int
    exact_collision_prob: float
    lookalike_collision_prob: float
    exact_alerts_per_day_low: float
    exact_alerts_per_day_med: float
    exact_alerts_per_day_high: float
    lookalike_alerts_per_day_low: float
    lookalike_alerts_per_day_med: float
    lookalike_alerts_per_day_high: float
    collision_expansion_ratio: float          # lookalike_prob / exact_prob


@dataclass
class WatchlistSimulationReport:
    """Consolidated report across watchlist sizes and operational traffic tiers."""
    tiers: List[WatchlistTierMetrics]
    policy_recommendation: str

    def to_markdown(self) -> str:
        lines = [
            "### Watchlist Collision & Operational False Alert Modeling",
            "",
            "| Watchlist Size (W) | Match Mode | Collision Prob / Veh | Low Traffic (1k/day) | Med Traffic (10k/day) | High Traffic (50k/day) |",
            "|---|---|---|---|---|---|",
        ]
        for t in self.tiers:
            lines.append(
                f"| {t.watchlist_size:,} | **Exact** | {t.exact_collision_prob:.2e} | "
                f"{t.exact_alerts_per_day_low:.2f} / day | {t.exact_alerts_per_day_med:.2f} / day | "
                f"{t.exact_alerts_per_day_high:.2f} / day |"
            )
            lines.append(
                f"| {t.watchlist_size:,} | **Look-alike** | {t.lookalike_collision_prob:.2e} | "
                f"{t.lookalike_alerts_per_day_low:.2f} / day | {t.lookalike_alerts_per_day_med:.2f} / day | "
                f"{t.lookalike_alerts_per_day_high:.2f} / day |"
            )
        lines.append("")
        lines.append(f"> [!IMPORTANT]\n> **Operational Policy Recommendation:** {self.policy_recommendation}")
        lines.append("")
        return "\n".join(lines)


def generate_synthetic_plate_pool(n: int = 20_000, seed: int = 42) -> List[str]:
    """Generates a representative background pool of Indian license plates."""
    rng = random.Random(seed)
    states = ["KA", "DL", "MH", "TN", "AP", "TS", "GJ", "UP", "HR", "KL"]
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    digits = "0123456789"

    pool = []
    for _ in range(n):
        st = rng.choice(states)
        dist = f"{rng.randint(1, 99):02d}"
        ser = "".join(rng.choices(letters, k=rng.randint(1, 2)))
        num = f"{rng.randint(1, 9999):04d}"
        pool.append(f"{st}{dist}{ser}{num}")
    return pool


def simulate_watchlist_collisions(
    benign_plates: Sequence[str],
    watchlist_sizes: Tuple[int, ...] = (10, 100, 1_000, 10_000),
    num_trials: int = 5,
    seed: int = 42,
) -> WatchlistSimulationReport:
    """Simulates random watchlist intersections with benign vehicle traffic."""
    norm_benign = [plate_norm(p) for p in benign_plates if plate_norm(p)]
    if len(norm_benign) < 1_000:
        # Augment with synthetic pool to enable accurate Monte Carlo collision rates
        extra = generate_synthetic_plate_pool(20_000 - len(norm_benign), seed=seed)
        norm_benign.extend(extra)

    key_benign = [plate_key(p) for p in norm_benign]
    rng = random.Random(seed)

    tiers: List[WatchlistTierMetrics] = []

    for w_size in watchlist_sizes:
        if w_size >= len(norm_benign):
            continue

        exact_collisions_sum = 0
        lookalike_collisions_sum = 0
        total_eval_samples = 0

        for trial in range(num_trials):
            # Sample random watchlist
            wl_sample = rng.sample(norm_benign, w_size)
            wl_exact_set: Set[str] = set(wl_sample)
            wl_key_set: Set[str] = {plate_key(p) for p in wl_sample}

            # Evaluate remaining vehicles as passing traffic
            eval_plates = [p for p in norm_benign if p not in wl_exact_set][:5_000]
            for p in eval_plates:
                total_eval_samples += 1
                if p in wl_exact_set:
                    exact_collisions_sum += 1
                if plate_key(p) in wl_key_set:
                    lookalike_collisions_sum += 1

        exact_prob = exact_collisions_sum / max(1, total_eval_samples)
        look_prob = lookalike_collisions_sum / max(1, total_eval_samples)
        expansion = (look_prob / exact_prob) if exact_prob > 0 else (look_prob * 1e6)

        tiers.append(
            WatchlistTierMetrics(
                watchlist_size=w_size,
                exact_collision_prob=exact_prob,
                lookalike_collision_prob=look_prob,
                exact_alerts_per_day_low=exact_prob * TRAFFIC_TIERS["low"],
                exact_alerts_per_day_med=exact_prob * TRAFFIC_TIERS["medium"],
                exact_alerts_per_day_high=exact_prob * TRAFFIC_TIERS["high"],
                lookalike_alerts_per_day_low=look_prob * TRAFFIC_TIERS["low"],
                lookalike_alerts_per_day_med=look_prob * TRAFFIC_TIERS["medium"],
                lookalike_alerts_per_day_high=look_prob * TRAFFIC_TIERS["high"],
                collision_expansion_ratio=expansion,
            )
        )

    recommendation = (
        "Exact matches drive high-priority automated alerts. "
        "Look-alike matches require multi-frame consensus stability (>= 3 agreeing reads) "
        "before dispatching to avoid alert fatigue at W >= 1,000."
    )

    return WatchlistSimulationReport(tiers=tiers, policy_recommendation=recommendation)
