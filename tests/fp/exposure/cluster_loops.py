"""Soak loop alert clustering and recurrence analysis.

Disentangles repeating anomalies in looped soak runs from independent false positives:
- Clusters raw alert timestamps modulo loop length (tolerance +/- 2s).
- Identifies distinct physical root causes rather than loop multiplier artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class SoakLoopCluster:
    cluster_id: str
    camera: str
    rule_type: str
    nominal_offset_s: float
    total_occurrences: int
    loop_period_s: float
    recurrence_rate: float  # fraction of loops in which it fired


def cluster_soak_alerts(
    raw_alerts: List[Dict[str, Any]],
    loop_period_s: float = 300.0,
    tolerance_s: float = 2.0,
) -> List[SoakLoopCluster]:
    """Clusters alerts across loop periods by matching modulo offset."""
    # Group by (camera, rule)
    groups: Dict[Tuple[str, str], List[float]] = {}
    for a in raw_alerts:
        cam = str(a.get("camera", "CAM-01"))
        rule = str(a.get("rule", "ZONE_ENTRY"))
        ts = float(a.get("timestamp_s", 0.0))
        groups.setdefault((cam, rule), []).append(ts)

    clusters: List[SoakLoopCluster] = []
    cluster_counter = 1

    for (cam, rule), timestamps in groups.items():
        if not timestamps:
            continue

        # Modulo offsets
        offsets = sorted([t % loop_period_s for t in timestamps])
        max_loop = max(int(t // loop_period_s) for t in timestamps) + 1

        # Cluster offsets within tolerance
        current_cluster: List[float] = [offsets[0]]

        for off in offsets[1:]:
            if abs(off - current_cluster[-1]) <= tolerance_s:
                current_cluster.append(off)
            else:
                avg_off = sum(current_cluster) / len(current_cluster)
                clusters.append(
                    SoakLoopCluster(
                        cluster_id=f"CLUSTER-{cluster_counter:03d}",
                        camera=cam,
                        rule_type=rule,
                        nominal_offset_s=round(avg_off, 1),
                        total_occurrences=len(current_cluster),
                        loop_period_s=loop_period_s,
                        recurrence_rate=min(1.0, len(current_cluster) / float(max_loop)),
                    )
                )
                cluster_counter += 1
                current_cluster = [off]

        if current_cluster:
            avg_off = sum(current_cluster) / len(current_cluster)
            clusters.append(
                SoakLoopCluster(
                    cluster_id=f"CLUSTER-{cluster_counter:03d}",
                    camera=cam,
                    rule_type=rule,
                    nominal_offset_s=round(avg_off, 1),
                    total_occurrences=len(current_cluster),
                    loop_period_s=loop_period_s,
                    recurrence_rate=min(1.0, len(current_cluster) / float(max_loop)),
                )
            )
            cluster_counter += 1

    return clusters
