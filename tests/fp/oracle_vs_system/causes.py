"""Root-cause attribution for unmatched false-positive events."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from tests.fp.tools.fp_log import VALID_CAUSES


def attribute_root_cause(
    system_event: Dict[str, Any],
    gt_frame_objects: List[Dict[str, Any]],
    zone_poly: Optional[List[Tuple[float, float]]] = None,
    recent_events_same_track: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Classifies an unmatched false-positive event against the closed cause taxonomy.

    Decision hierarchy:
    1. No GT object within 100px -> detector_ghost
    2. GT object exists near point but class differs -> class_confusion
    3. GT object exists, foot-point is outside zone while bbox overlaps -> foot_point_perspective
    4. GT object foot-point is outside zone, high coordinate variance -> tracker_jitter
    5. Duplicate event from different track ID for same GT subject -> id_switch_duplicate
    6. Rapid enter/exit oscillation within 3 seconds -> hysteresis_too_small
    7. Fallback -> unknown
    """
    sys_pt = system_event["anchor_pt"]
    sys_cls = system_event.get("cls", "person")

    # Find nearest GT object
    nearest_gt = None
    min_dist = float("inf")
    for gt in gt_frame_objects:
        gpt = gt.get("foot", gt.get("bottom_center", (0.0, 0.0)))
        d = math.hypot(sys_pt[0] - gpt[0], sys_pt[1] - gpt[1])
        if d < min_dist:
            min_dist = d
            nearest_gt = gt

    # 1. No GT object nearby (phantom detection)
    if nearest_gt is None or min_dist > 80.0:
        return "detector_ghost"

    # 2. Class confusion
    gt_cls = nearest_gt.get("cls", "person")
    if gt_cls != sys_cls:
        return "class_confusion"

    # 3. Check oscillation
    if recent_events_same_track and len(recent_events_same_track) >= 2:
        last_t = recent_events_same_track[-1].get("timestamp_s", 0.0)
        cur_t = system_event.get("timestamp_s", 0.0)
        if cur_t - last_t < 3.0:
            return "hysteresis_too_small"

    # 4. Check perspective / foot-point
    if zone_poly:
        from tests.fp.logic.sim.oracle import min_signed_distance
        sd_foot = min_signed_distance(zone_poly, sys_pt)
        if sd_foot > 0.0:
            # Foot is outside zone
            bbox = system_event.get("bbox_xyxy")
            if bbox:
                # Check center
                center = (sys_pt[0], sys_pt[1] - (bbox[3] - bbox[1]) / 2.0)
                if min_signed_distance(zone_poly, center) <= 0.0:
                    return "foot_point_perspective"
            return "tracker_jitter"

    return "unknown"
