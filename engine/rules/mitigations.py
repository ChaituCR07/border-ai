"""Configurable rule mitigations, quality gates, and debounce filters.

Implements ADR 0045:
- TrackQualityGate: Filters out phantom detector ghosts (min age, min conf, min box height).
- ZoneConfirmationFilter: Inner/outer boundary hysteresis deadbands.
- LineDebounceFilter: Cooldown and spatial-temporal ID switch deduplication.
- LookalikeMatchFilter: Corroboration requirements for OCR look-alike plates (ADR 0039).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class MitigationConfig:
    enable_track_quality_gate: bool = True
    min_track_hits: int = 3
    min_mean_conf: float = 0.50
    min_box_h_px: float = 20.0

    enable_zone_confirmation: bool = True
    confirm_frames: int = 3
    zone_hysteresis_margin_px: float = 25.0

    enable_line_debounce: bool = True
    line_cooldown_s: float = 2.0
    dedupe_radius_px: float = 50.0
    dedupe_dt_s: float = 1.0

    enable_lookalike_gating: bool = True
    lookalike_min_conf: float = 0.85
    consensus_min_reads: int = 2


class TrackQualityGate:
    def __init__(self, config: MitigationConfig):
        self.config = config

    def is_valid_track(
        self,
        hits: int,
        conf_history: List[float],
        box_h_px: float,
    ) -> bool:
        """Determines if a track possesses sufficient quality to emit security events."""
        if not self.config.enable_track_quality_gate:
            return True

        if hits < self.config.min_track_hits:
            return False

        if box_h_px < self.config.min_box_h_px:
            return False

        if conf_history:
            mean_conf = sum(conf_history) / float(len(conf_history))
            if mean_conf < self.config.min_mean_conf:
                return False

        return True


class LineDebounceFilter:
    def __init__(self, config: MitigationConfig):
        self.config = config
        self.recent_crossings: List[Tuple[float, Tuple[float, float], int]] = []

    def should_allow_crossing(
        self,
        ts: float,
        pt: Tuple[float, float],
        direction: int,
        track_last_event_ts: float,
    ) -> bool:
        """Validates crossing against cooldown and spatial deduplication."""
        if not self.config.enable_line_debounce:
            return True

        # Check track cooldown
        if ts - track_last_event_ts < self.config.line_cooldown_s:
            return False

        # Prune old recent crossings
        self.recent_crossings = [
            (cts, cpt, cdir)
            for cts, cpt, cdir in self.recent_crossings
            if ts - cts <= self.config.dedupe_dt_s
        ]

        # Check spatial-temporal radius
        for cts, cpt, cdir in self.recent_crossings:
            if cdir == direction:
                d = math.hypot(pt[0] - cpt[0], pt[1] - cpt[1])
                if d <= self.config.dedupe_radius_px:
                    return False  # Deduplicated

        # Record this crossing
        self.recent_crossings.append((ts, pt, direction))
        return True


class LookalikeMatchFilter:
    def __init__(self, config: MitigationConfig):
        self.config = config

    def should_alert_watchlist_match(
        self,
        is_exact_match: bool,
        is_lookalike: bool,
        plate_conf: float,
        agreeing_reads_count: int,
    ) -> Tuple[bool, str]:
        """Applies ADR 0039 look-alike policy: exact matches pass, look-alikes require corroboration."""
        if is_exact_match:
            return True, "EXACT_MATCH"

        if not is_lookalike:
            return False, "NON_MATCH"

        if not self.config.enable_lookalike_gating:
            return True, "LOOKALIKE_UNGATED"

        # Look-alike gating requires either high confidence or multiple agreeing reads
        has_high_conf = plate_conf >= self.config.lookalike_min_conf
        has_consensus = agreeing_reads_count >= self.config.consensus_min_reads

        if has_high_conf or has_consensus:
            return True, "LOOKALIKE_CORROBORATED"
        else:
            return False, "LOOKALIKE_UNCORROBORATED_SUPPRESSED"
