import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.behaviour.rules_config import load_behaviour_config  # noqa: E402
from app.threat.calc import evaluate_items  # noqa: E402
from app.threat.config import parse_scoring_config  # noqa: E402

PLAN = [
    ("Plan scenario 1: restricted area at night", ["line_crossing", "zone_violation", "after_hours"], 60, "HIGH"),
    ("Plan scenario 2 / Day 12 example: watchlisted vehicle",
     ["watchlist_vehicle:alert", "zone_violation", "direction_violation", "after_hours"], 100, "CRITICAL"),
    ("Plan section 5 illustration without an 'unknown person' weight",
     ["zone_violation", "after_hours", "loitering"], None, None),
]


def run(scoring, points, items):
    out = evaluate_items(scoring, points, items)
    for kind, label, pts in out["rows"]:
        print(f"  {kind:<28}{label:<48}{pts:>4}")
    r = out["result"]
    notes = []
    if r.excluded:
        notes.append(f"not counted (double counting): {', '.join(r.excluded)}")
    if r.bonus:
        notes.append(f"bonus +{r.bonus}")
    if r.capped:
        notes.append(f"capped from {r.raw}")
    print(f"  => score {r.score}, level {out['level']}" + (f"   ({'; '.join(notes)})" if notes else ""))
    return r.score, out["level"]


def main():
    ap = argparse.ArgumentParser(description="What score and level does this evidence give?")
    ap.add_argument("items", nargs="*", help="evidence kinds, e.g. zone_violation watchlist_vehicle:review")
    ap.add_argument("--rules", default=str(config.CONFIG_DIR / "rules.json"))
    ap.add_argument("--plan", action="store_true", help="check the plan's own examples")
    args = ap.parse_args()

    data = json.loads(Path(args.rules).read_text())
    scoring = parse_scoring_config(data, source=args.rules)
    points = {r.event_type: r.points for r in load_behaviour_config(Path(args.rules)).rules}
    if args.items:
        run(scoring, points, args.items)
    if args.plan:
        for title, items, want_score, want_level in PLAN:
            print(f"\n{title}")
            score, level = run(scoring, points, items)
            if want_score is not None:
                print(f"  plan says {want_score} {want_level}: {'OK' if (score, level) == (want_score, want_level) else 'DIFFERENT'}")
    if not args.items and not args.plan:
        ap.print_help()


if __name__ == "__main__":
    main()
