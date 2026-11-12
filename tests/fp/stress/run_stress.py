"""Camera view-shift tolerance and perturbation benchmark runner."""

from __future__ import annotations

from typing import Dict, List, Tuple
from tests.fp.logic.sim.track_sim import walk, to_frames
from tests.fp.logic.sim.zone_evaluator import ZoneEvaluator
from tests.fp.stress.augment_video import StressConfig, generate_stress_stream


def evaluate_camera_shift_tolerance(
    zone_poly: List[Tuple[float, float]],
    margin_px: float = 20.0,
    max_shift_px: float = 50.0,
    step_px: float = 5.0,
) -> Dict[str, Any]:
    """Sweeps static camera translation offsets to measure how many pixels of bump or drift the zone can tolerate before false alerts appear."""
    # Person walking parallel to zone boundary, 25px outside boundary
    # Zone boundary is at y=200. Person at y=175.
    base_track = walk([(300.0, 175.0), (700.0, 175.0)], speed_px_s=50.0, fps=25.0, seed=1)
    base_frames = list(to_frames([base_track], fps=25.0))

    shift_results: List[Tuple[float, int]] = []
    tolerated_shift = 0.0

    shifts = [float(s) for s in range(0, int(max_shift_px) + 1, int(step_px))]

    for shift in shifts:
        # Shift coordinate towards zone (+dy)
        cfg = StressConfig(shake_sigma_px=0.0, drift_rate_px_s=0.0)
        # Manually apply pure translation
        shifted_frames = []
        for ts, dets in base_frames:
            from tests.fp.stress.augment_video import apply_camera_shake
            shifted = apply_camera_shake(dets, (0.0, shift))
            shifted_frames.append((ts, shifted))

        evaluator = ZoneEvaluator("ZONE-01", zone_poly, margin_px=margin_px, confirm_frames=3)
        events = []
        for ts, dets in shifted_frames:
            events.extend(evaluator.process_frame(ts, dets))

        num_fps = len([e for e in events if e.event_type == "ZONE_ENTER"])
        shift_results.append((shift, num_fps))

        if num_fps == 0:
            tolerated_shift = shift

    return {
        "zone_margin_px": margin_px,
        "max_tolerated_shift_px": tolerated_shift,
        "shift_curve": shift_results,
    }
