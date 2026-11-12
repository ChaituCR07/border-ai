"""Replay harness running ground-truth and predicted tracks through the identical rule engine."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from tests.fp.logic.sim.zone_evaluator import ZoneEvaluator


def replay_zone_evaluation(
    tracks_frames: List[Tuple[float, List[Dict[str, Any]]]],
    zone_poly: List[Tuple[float, float]],
    margin_px: float = 20.0,
    confirm_frames: int = 3,
) -> List[Dict[str, Any]]:
    """Pushes a frame stream through ZoneEvaluator and returns standardized event dicts."""
    evaluator = ZoneEvaluator("ZONE-01", zone_poly, margin_px=margin_px, confirm_frames=confirm_frames)
    events: List[Dict[str, Any]] = []

    for ts, detections in tracks_frames:
        evs = evaluator.process_frame(ts, detections)
        for ev in evs:
            events.append({
                "event_type": ev.event_type,
                "zone_id": ev.zone_id,
                "track_id": ev.track_id,
                "timestamp_s": ev.timestamp_s,
                "anchor_pt": ev.anchor_pt,
                "score": ev.score,
            })

    return events
