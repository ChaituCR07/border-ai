import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app.identity.config import ReidConfig  # noqa: E402
from app.identity.factory import build_embedder  # noqa: E402
from app.identity.metrics import pair_similarities, rank_k_accuracy, threshold_table  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--embedder", default="color_layout", choices=["color_layout", "onnx"])
    args = ap.parse_args()

    cfg = ReidConfig(embedder=args.embedder)
    embedder = build_embedder(cfg)
    by_cam = {}
    for person_dir in sorted(p for p in Path(args.folder).iterdir() if p.is_dir()):
        for img_path in sorted(person_dir.iterdir()):
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            cam = img_path.name.split("_")[0]
            by_cam.setdefault(cam, []).append((person_dir.name, embedder.embed(img)))

    cams = sorted(by_cam)
    if len(cams) < 2:
        sys.exit("Need images from at least two cameras (file names like cam1_001.jpg, cam2_001.jpg)")
    print(f"embedder {embedder.name} | cameras {cams} | "
          + ", ".join(f"{c}: {len(by_cam[c])} crops" for c in cams))

    for a in cams:
        for b in cams:
            if a >= b:
                continue
            for q_cam, g_cam in ((a, b), (b, a)):
                acc = rank_k_accuracy(by_cam[q_cam], by_cam[g_cam], ks=(1, 5))
                print(f"query {q_cam} -> gallery {g_cam}: rank-1 {acc[1]:.1%}  rank-5 {acc[5]:.1%}")

    # same-person vs different-person similarity across cameras
    genuine, impostor = [], []
    for ca in cams:
        for cb in cams:
            if ca >= cb:
                continue
            for pa, ea in by_cam[ca]:
                for pb, eb in by_cam[cb]:
                    (genuine if pa == pb else impostor).append(float(np.dot(ea, eb)))
    if genuine and impostor:
        print(f"\ncross-camera same person: mean {np.mean(genuine):.3f} | different people: mean {np.mean(impostor):.3f}")
        print(f"{'threshold':>9}{'TAR':>8}{'FAR':>9}")
        for t, tar, far in threshold_table(genuine, impostor, np.round(np.arange(0.5, 1.0, 0.05), 2)):
            print(f"{t:>9.2f}{tar:>8.1%}{far:>9.1%}")
    print("\nChoose reid.similarity_threshold from this table; with the color baseline expect weak separation.")


if __name__ == "__main__":
    main()
