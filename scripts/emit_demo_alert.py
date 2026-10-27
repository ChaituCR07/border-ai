#!/usr/bin/env python3
"""
Emit a realistic demo alert to the real Redis streams (surveillance.alerts and surveillance.events).
Used to demonstrate sub-second live alert push to the Command Center dashboard.
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

try:
    import redis
except ImportError:
    print("Error: redis-py is required. Run in virtualenv.", file=sys.stderr)
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Emit synthetic threat alert to Redis streams")
    parser.add_argument("--camera", default="CAM-03", help="Camera ID (default: CAM-03)")
    parser.add_argument("--plate", default="KA01AB1234", help="License plate (default: KA01AB1234)")
    parser.add_argument("--score", type=int, default=92, help="Threat score 0-100 (default: 92)")
    parser.add_argument("--priority", default="CRITICAL", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                        help="Severity priority (default: CRITICAL)")
    parser.add_argument("--event-type", default="RESTRICTED_ZONE_ENTRY", help="Event classification")
    parser.add_argument("--summary", default="Restricted Zone Entry", help="Alert summary text")
    parser.add_argument("--burst", type=int, default=1, help="Number of alerts to burst emit")
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between burst events")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                        help="Redis connection URL")
    return parser.parse_args()


def emit_alert(r: redis.Redis, args, idx: int) -> str:
    alert_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ms = int(time.time() * 1000)

    data = {
        "schema": 1,
        "event_id": event_id,
        "type": "THREAT_ALERT",
        "camera": args.camera,
        "camera_id": args.camera,
        "track_id": 42 + idx,
        "timestamp": now_iso,
        "severity": args.priority,
        "threat_score": args.score,
        "plate": args.plate,
        "details": {
            "alert_id": alert_id,
            "priority": args.priority,
            "threat_score": args.score,
            "entity": args.plate,
            "summary": args.summary,
            "event_type": args.event_type,
            "snapshot_path": f"{args.camera}/snap_{alert_id[:8]}.jpg",
            "plate": args.plate,
        },
    }

    fields = {
        "v": "1",
        "event_id": event_id,
        "type": "THREAT_ALERT",
        "camera": args.camera,
        "ts": str(now_ms),
        "severity": args.priority,
        "run_id": "demo-alert-run",
        "data": json.dumps(data, separators=(",", ":")),
    }

    # Publish to both surveillance.alerts (live WebSocket tail) and surveillance.events (Postgres sink)
    stream_id = r.xadd("surveillance.alerts", fields, maxlen=10000)
    r.xadd("surveillance.events", fields, maxlen=100000)

    print(f"🚨 [DEMO ALERT {idx+1}/{args.burst}] Emitted to surveillance.alerts (Stream ID: {stream_id.decode() if isinstance(stream_id, bytes) else stream_id})")
    print(f"   Alert ID:     {alert_id}")
    print(f"   Camera:       {args.camera}")
    print(f"   Priority:     {args.priority}")
    print(f"   Score:        {args.score} / 100")
    print(f"   Plate:        {args.plate}")
    print(f"   Event Type:   {args.event_type}")
    print(f"   Timestamp:    {now_iso}")

    return alert_id


def main():
    args = parse_args()
    r = redis.from_url(args.redis_url)

    for i in range(args.burst):
        emit_alert(r, args, i)
        if i + 1 < args.burst:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
