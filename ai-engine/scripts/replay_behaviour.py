import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.behaviour.factory import build_behaviour  # noqa: E402
from app.behaviour.replay import load_events, replay  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Run the behaviour rules over a recorded events.jsonl")
    ap.add_argument("--events", required=True, help="outputs/runs/<run>/events.jsonl")
    ap.add_argument("--rules", help="rules file to try (default configs/rules.json)")
    ap.add_argument("--tick", type=float, default=1.0)
    args = ap.parse_args()

    engine = build_behaviour(args.rules)
    if engine is None:
        sys.exit("No rules file found")
    events = load_events(args.events)
    out = replay(events, engine, tick_s=args.tick)

    print(f"{len(events)} recorded observations -> {len(out)} behaviour event(s)\n")
    for e in sorted(out, key=lambda e: e.timestamp):
        print(f"{e.timestamp:>14.1f}  {e.camera_id}  #{e.track_id:<4} {e.type:<36} {e.details['severity']:<9}"
              f"{e.details['points']:>4}  {'; '.join(e.details['reasons'])}")
    print("\ncounts:", dict(Counter(f"{e.type}:{e.rule_id}" for e in out)))


if __name__ == "__main__":
    main()
