import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.behaviour.expect import compare_counts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True, help="outputs/runs/<run>/summary.json")
    ap.add_argument("--expect", required=True, help="docs/ground_truth/behaviour_<clip>.json")
    ap.add_argument("--tolerance", type=int, default=0)
    ap.add_argument("--only", nargs="*", help="only compare keys starting with these prefixes")
    args = ap.parse_args()

    counts = json.load(open(args.summary))["event_counts"]
    expected = json.load(open(args.expect))["expected"]
    if args.only:
        counts = {k: v for k, v in counts.items() if k.startswith(tuple(args.only))}
        expected = {k: v for k, v in expected.items() if k.startswith(tuple(args.only))}
    rows, ok = compare_counts(counts, expected, args.tolerance)
    print(f"{'event':<44}{'expected':>9}{'got':>6}  result")
    for r in rows:
        print(f"{r['key']:<44}{r['expected']:>9}{r['got']:>6}  {'PASS' if r['pass'] else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
