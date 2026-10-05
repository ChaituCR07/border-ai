import argparse
import csv
import math
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_csv(path: Path) -> List[Dict]:
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "track_id": int(r["track_id"]),
                "class": r["class"],
                "first_s": float(r["first_s"]),
                "last_s": float(r["last_s"]),
                "duration_s": float(r["duration_s"]),
                "hits": int(r["hits"]),
                "state": r["state"],
                "displacement_px": float(r["displacement_px"]),
            })
    return rows


def analyze_tracks(tracks: List[Dict]) -> Dict:
    if not tracks:
        return {"total_tracks": 0, "active": 0, "removed": 0, "avg_duration_s": 0.0,
                "avg_displacement_px": 0.0, "avg_speed_px_s": 0.0}

    total = len(tracks)
    durations = [t["duration_s"] for t in tracks]
    displacements = [t["displacement_px"] for t in tracks]
    speeds = [t["displacement_px"] / max(t["duration_s"], 0.001) for t in tracks]

    return {
        "total_tracks": total,
        "active": sum(1 for t in tracks if t["state"] == "ACTIVE"),
        "removed": sum(1 for t in tracks if t["state"] == "REMOVED"),
        "avg_duration_s": round(sum(durations) / total, 2),
        "max_duration_s": round(max(durations), 2),
        "avg_displacement_px": round(sum(displacements) / total, 1),
        "max_displacement_px": round(max(displacements), 1),
        "avg_speed_px_s": round(sum(speeds) / total, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze tracked objects CSV dataset")
    parser.add_argument("--csv", required=True, help="Path to track CSV")
    parser.add_argument("--output-md", help="Optional markdown output summary path")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        sys.exit(f"File not found: {csv_path}")

    tracks = load_csv(csv_path)
    metrics = analyze_tracks(tracks)

    print("\n--- Track Kinematic Analysis ---")
    print(f"File: {csv_path.name}")
    for k, v in metrics.items():
        print(f"  {k:.<25} {v}")

    if args.output_md:
        out_p = Path(args.output_md)
        with open(out_p, "w") as f:
            f.write(f"# Tracking Analysis: {csv_path.stem}\n\n")
            f.write("| Metric | Value |\n|---|---|\n")
            for k, v in metrics.items():
                f.write(f"| {k} | {v} |\n")
        print(f"\nReport written to: {out_p}")


if __name__ == "__main__":
    main()
