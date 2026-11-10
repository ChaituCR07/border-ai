"""Database storage capacity model and disk footprint projections.

Calculates:
- Events per camera-hour across workload profiles
- Average bytes per row on PostgreSQL tables (events, alerts, tracks)
- Storage projections (GB/month) for N in {1, 4, 8, 16, 32} cameras
- Proves ~99% storage reduction of TRACK_SUMMARY vs raw detection logging
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class CapacityProjection:
    camera_count: int
    workload: str
    events_per_day: int
    alerts_per_day: int
    raw_frame_db_gb_month: float
    track_summary_db_gb_month: float
    storage_savings_pct: float
    snapshot_disk_gb_month: float
    total_gb_30_days: float
    total_gb_90_days: float
    total_gb_365_days: float


# Average stored row sizes (in bytes, including PostgreSQL page overhead and B-tree indexes)
BYTES_PER_EVENT_ROW = 420.0
BYTES_PER_ALERT_ROW = 1250.0
BYTES_PER_RAW_DETECTION = 280.0
AVG_SNAPSHOT_IMAGE_BYTES = 185_000.0  # 185 KB JPEG snapshot


def compute_capacity_projections(cameras: int = 4, workload: str = "typical") -> CapacityProjection:
    """Compute exact disk footprint and multi-retention storage projections."""
    # Workload events/hour per camera
    events_per_cam_hour = {"light": 45, "typical": 180, "heavy": 520}.get(workload, 180)
    alerts_per_cam_hour = {"light": 0.5, "typical": 2.5, "heavy": 8.0}.get(workload, 2.5)

    daily_events = int(cameras * events_per_cam_hour * 24)
    daily_alerts = int(cameras * alerts_per_cam_hour * 24)

    # 1. Day 14 TRACK_SUMMARY event storage (1 summary event per completed trajectory)
    daily_summary_bytes = daily_events * BYTES_PER_EVENT_ROW
    daily_alert_bytes = daily_alerts * BYTES_PER_ALERT_ROW
    daily_db_gb = (daily_summary_bytes + daily_alert_bytes) / (1024.0 ** 3)
    monthly_db_gb = daily_db_gb * 30.0

    # 2. Raw unaggregated detection logging (logging every box at 10 FPS)
    # Average 4 detections/frame * 10 FPS = 40 detections/sec = 144,000 rows/hour/cam
    daily_raw_detections = cameras * 144_000 * 24
    daily_raw_bytes = daily_raw_detections * BYTES_PER_RAW_DETECTION
    monthly_raw_gb = (daily_raw_bytes / (1024.0 ** 3)) * 30.0

    savings_pct = max(0.0, (1.0 - (monthly_db_gb / monthly_raw_gb))) * 100.0

    # 3. Snapshot disk storage (stored on disk, referenced by URL)
    daily_snapshot_gb = (daily_alerts * AVG_SNAPSHOT_IMAGE_BYTES) / (1024.0 ** 3)
    monthly_snapshot_gb = daily_snapshot_gb * 30.0

    total_monthly_gb = monthly_db_gb + monthly_snapshot_gb

    return CapacityProjection(
        camera_count=cameras,
        workload=workload,
        events_per_day=daily_events,
        alerts_per_day=daily_alerts,
        raw_frame_db_gb_month=round(monthly_raw_gb, 2),
        track_summary_db_gb_month=round(monthly_db_gb, 2),
        storage_savings_pct=round(savings_pct, 2),
        snapshot_disk_gb_month=round(monthly_snapshot_gb, 2),
        total_gb_30_days=round(total_monthly_gb, 2),
        total_gb_90_days=round(total_monthly_gb * 3.0, 2),
        total_gb_365_days=round(total_monthly_gb * 12.17, 2),
    )


def generate_capacity_table() -> List[CapacityProjection]:
    cams = [1, 4, 8, 16, 32]
    return [compute_capacity_projections(c, "typical") for c in cams]


if __name__ == "__main__":
    projs = generate_capacity_table()
    print("=" * 80)
    print(" BorderVision Storage Capacity Projections (Typical Workload)")
    print("=" * 80)
    print(f"| Cameras | Daily Events | Daily Alerts | TrackSummary DB/mo | Raw DB/mo | Savings | Total (30d) | Total (90d) | Total (1yr) |")
    for p in projs:
        print(
            f"| {p.camera_count:7d} | {p.events_per_day:12,d} | {p.alerts_per_day:12,d} | "
            f"{p.track_summary_db_gb_month:15.2f} GB | {p.raw_frame_db_gb_month:7.1f} GB | {p.storage_savings_pct:6.1f}% | "
            f"{p.total_gb_30_days:9.1f} GB | {p.total_gb_90_days:9.1f} GB | {p.total_gb_365_days:9.1f} GB |"
        )
