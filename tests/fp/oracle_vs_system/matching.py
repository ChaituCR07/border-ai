"""Event matching between system events and oracle ground truth events."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class RuleEventMatch:
    system_event: Dict[str, Any]
    oracle_event: Optional[Dict[str, Any]]
    time_diff_s: float
    distance_px: float
    is_tp: bool


def match_events(
    system_events: List[Dict[str, Any]],
    oracle_events: List[Dict[str, Any]],
    time_tol_s: float = 1.0,
    dist_tol_px: float = 80.0,
) -> Tuple[List[RuleEventMatch], List[Dict[str, Any]]]:
    """Matches pipeline events to oracle events (one-to-one).

    Returns:
        (matches, unmatched_oracle_events)
    """
    matched_oracle_indices: Set[int] = set()
    matches: List[RuleEventMatch] = []

    for sys_ev in system_events:
        sys_ts = float(sys_ev["timestamp_s"])
        sys_pt = sys_ev["anchor_pt"]
        sys_type = sys_ev["event_type"]

        best_idx: Optional[int] = None
        best_dt = float("inf")
        best_dist = float("inf")

        for idx, o_ev in enumerate(oracle_events):
            if idx in matched_oracle_indices:
                continue
            if o_ev["event_type"] != sys_type:
                continue

            o_ts = float(o_ev["timestamp_s"])
            dt = abs(sys_ts - o_ts)
            if dt > time_tol_s:
                continue

            o_pt = o_ev["anchor_pt"]
            dist = math.hypot(sys_pt[0] - o_pt[0], sys_pt[1] - o_pt[1])
            if dist > dist_tol_px:
                continue

            if dt < best_dt:
                best_dt = dt
                best_dist = dist
                best_idx = idx

        if best_idx is not None:
            matched_oracle_indices.add(best_idx)
            matches.append(
                RuleEventMatch(
                    system_event=sys_ev,
                    oracle_event=oracle_events[best_idx],
                    time_diff_s=best_dt,
                    distance_px=best_dist,
                    is_tp=True,
                )
            )
        else:
            matches.append(
                RuleEventMatch(
                    system_event=sys_ev,
                    oracle_event=None,
                    time_diff_s=float("nan"),
                    distance_px=float("nan"),
                    is_tp=False,
                )
            )

    unmatched_oracle = [
        o_ev for idx, o_ev in enumerate(oracle_events) if idx not in matched_oracle_indices
    ]

    return matches, unmatched_oracle
