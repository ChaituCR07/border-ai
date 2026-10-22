import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.events.config import EventsConfig  # noqa: E402
from app.events.factory import build_redis_client  # noqa: E402
from app.events.processor import ConsoleAlertSink, EventProcessor, JsonlFileSink  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Consume the event stream and hand events to sinks")
    ap.add_argument("--consumer", help="consumer name (default from the configuration)")
    ap.add_argument("--start", choices=["0", "$"], help="where a NEW group starts reading")
    ap.add_argument("--out", default=str(config.OUTPUT_DIR / "processed" / "events.jsonl"))
    ap.add_argument("--stats-every", type=float, default=5.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = EventsConfig.from_config(config.load_app_config().get("events"))
    if args.start:
        cfg.processor.start = args.start
    sinks = [JsonlFileSink(args.out), ConsoleAlertSink()]       # tomorrow: PostgresEventSink
    proc = EventProcessor(build_redis_client(cfg), sinks, cfg, consumer=args.consumer)

    signal.signal(signal.SIGINT, lambda *_: proc.stop())
    signal.signal(signal.SIGTERM, lambda *_: proc.stop())
    worker = threading.Thread(target=proc.run_forever, daemon=True)
    worker.start()
    print(f"processor {proc.consumer} in group {cfg.processor.group} reading {cfg.stream} -> {args.out}")
    last = time.time()
    while worker.is_alive():
        time.sleep(0.25)
        if time.time() - last >= args.stats_every:
            print("stats:", proc.status())
            last = time.time()
    for sink in sinks:
        sink.close()
    print("stopped:", proc.status())


if __name__ == "__main__":
    main()
