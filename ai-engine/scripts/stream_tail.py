import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.events.config import EventsConfig  # noqa: E402
from app.events.factory import build_redis_client  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Show the newest entries of a stream")
    ap.add_argument("--stream", choices=["events", "alerts", "dead"], default="events")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--follow", action="store_true")
    args = ap.parse_args()

    cfg = EventsConfig.from_config(config.load_app_config().get("events"))
    stream = {"events": cfg.stream, "alerts": cfg.alerts_stream, "dead": cfg.dead_stream}[args.stream]
    client, last = build_redis_client(cfg), None
    while True:
        for mid, fields in client.range(stream, args.count if last is None else 1000):
            if last is not None and tuple(map(int, mid.split("-"))) <= tuple(map(int, last.split("-"))):
                continue
            last = mid
            line = f"{mid}  {fields.get('type', '?'):<30}{fields.get('camera', '?'):<10}{fields.get('severity', ''):<9}"
            if "dead_reason" in fields:
                line += f" DEAD: {fields['dead_reason']}"
            print(line + f" {fields.get('event_id', '')[:12]}")
        if not args.follow:
            return
        time.sleep(1)


if __name__ == "__main__":
    main()
