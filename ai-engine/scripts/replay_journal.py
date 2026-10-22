import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.events.config import EventsConfig  # noqa: E402
from app.events.factory import build_redis_client  # noqa: E402
from app.events.journal import publish_journal  # noqa: E402
from app.events.publisher import StreamTransport, TransportUnavailable  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Publish a recorded events.jsonl to the event stream")
    ap.add_argument("--events", required=True, help="outputs/runs/<run>/events.jsonl")
    ap.add_argument("--run-id", default="", help="run id to stamp on the envelopes (default: the folder name)")
    ap.add_argument("--rate", type=float, help="events per second (default: as fast as possible)")
    args = ap.parse_args()

    cfg = EventsConfig.from_config(config.load_app_config().get("events"))
    run_id = args.run_id or Path(args.events).resolve().parent.name
    try:
        n = publish_journal(args.events, StreamTransport(build_redis_client(cfg), cfg), run_id, rate_per_s=args.rate)
    except TransportUnavailable as e:
        sys.exit(f"The event bus is still unavailable: {e}")
    print(f"published {n} events from {args.events} (duplicates of earlier deliveries are dropped by the consumers)")


if __name__ == "__main__":
    main()
