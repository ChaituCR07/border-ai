import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app import config  # noqa: E402
from app.identity.config import IdentityConfig  # noqa: E402
from app.identity.face import face_quality  # noqa: E402
from app.identity.factory import build_face_engine  # noqa: E402
from app.identity.metrics import (equal_error_rate, expected_false_matches, pair_similarities,  # noqa: E402
                                  threshold_for_far, threshold_table)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="one sub-folder per person")
    ap.add_argument("--no-quality-gate", action="store_true")
    ap.add_argument("--csv", default=str(config.OUTPUT_DIR / "face_eval.csv"))
    ap.add_argument("--gallery-size", type=int, default=50, help="enrolled faces in your planned deployment")
    ap.add_argument("--strangers-per-day", type=int, default=1000)
    args = ap.parse_args()

    app_cfg = config.load_app_config()
    cfg = IdentityConfig.from_config(app_cfg.get("identity"))
    engine = build_face_engine(cfg.face, app_cfg.get("model", {}).get("device", "auto"))
    if engine is None:
        sys.exit("No face engine available")

    people, skipped = {}, {}
    for person_dir in sorted(p for p in Path(args.folder).iterdir() if p.is_dir()):
        for img_path in sorted(person_dir.iterdir()):
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            faces = engine.detect(img)
            if not faces:
                skipped.setdefault("no_face", []).append(str(img_path))
                continue
            if not args.no_quality_gate:
                q = face_quality(img, faces[0], cfg.face)
                if not q.ok:
                    skipped.setdefault(q.reason, []).append(str(img_path))
                    continue
            people.setdefault(person_dir.name, []).append(engine.embed(img, faces[0]))

    people = {p: v for p, v in people.items() if len(v) >= 2}
    genuine, impostor = pair_similarities(people)
    print(f"model {engine.model_name} | {len(people)} people with 2+ usable photos | "
          f"{sum(len(v) for v in people.values())} photos | skipped: {{{', '.join(f'{k}: {len(v)}' for k, v in skipped.items())}}}")
    if not genuine or not impostor:
        sys.exit("Need at least two people with two or more usable photos each")
    print(f"genuine pairs {len(genuine)}  (mean {np.mean(genuine):.3f}, min {np.min(genuine):.3f})")
    print(f"impostor pairs {len(impostor)}  (mean {np.mean(impostor):.3f}, max {np.max(impostor):.3f})")

    eer, eer_t = equal_error_rate(genuine, impostor)
    print(f"equal error rate ~{eer:.1%} at threshold {eer_t:.3f}")

    thresholds = np.round(np.arange(0.20, 0.95, 0.05), 2)
    rows = threshold_table(genuine, impostor, thresholds)
    print(f"\n{'threshold':>9}{'TAR':>8}{'FAR':>10}   false-matching strangers/day (gallery {args.gallery_size}, "
          f"{args.strangers_per_day} strangers)")
    for t, tar, far in rows:
        print(f"{t:>9.2f}{tar:>8.1%}{far:>10.2%}   {expected_false_matches(far, args.gallery_size, args.strangers_per_day):>8.1f}")

    for target in (0.01, 0.001):
        t = threshold_for_far(genuine, impostor, target)
        print(f"smallest threshold with FAR <= {target:.1%}: {t:.3f}   "
              f"(resolution limit: {1 / len(impostor):.2%} with {len(impostor)} impostor pairs)")

    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["threshold", "TAR", "FAR"])
        w.writerows(rows)
    print("\ntable saved to", args.csv)
    print("Reminder: more identities and more varied photos make these numbers more trustworthy; "
          "with a handful of people they are only indicative.")


if __name__ == "__main__":
    main()
