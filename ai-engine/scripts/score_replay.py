import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.behaviour.replay import load_events, replay  # noqa: E402
from app.threat.factory import build_scorer  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Run threat scoring over a recorded events.jsonl")
    ap.add_argument("--events", required=True, help="outputs/runs/<run>/events.jsonl")
    ap.add_argument("--rules", help="rules file with the scoring section to try (default configs/rules.json)")
    ap.add_argument("--tick", type=float, default=1.0)
    args = ap.parse_args()

    scorer = build_scorer(args.rules)
    if scorer is None:
        sys.exit("No scoring section found")
    alerts = replay(load_events(args.events), scorer, tick_s=args.tick, keep_behaviour=True)

    print(f"{len(alerts)} alert(s)\n")
    for a in sorted(alerts, key=lambda e: e.timestamp):
        d = a.details
        print(f"{a.timestamp:>14.1f}  {a.camera_id}  {d['entity']:<24}{d['level']:<9}{d['threat_score']:>4}  {d['summary']}")
    print("\nfinal entity scores:")
    for s in sorted(scorer.all_states(), key=lambda s: -s.score):
        print(f"  {s.entity:<26}{s.score:>4}  {s.level:<9}{s.object_class:<10}plate {s.plate or '-'}")


if __name__ == "__main__":
    main()
