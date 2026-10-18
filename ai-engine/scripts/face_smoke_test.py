import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.identity.config import IdentityConfig  # noqa: E402
from app.identity.embeddings import cosine  # noqa: E402
from app.identity.face import face_quality  # noqa: E402
from app.identity.factory import build_face_engine  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Detect faces and embed them. Use consenting subjects only.")
    ap.add_argument("--image", required=True)
    ap.add_argument("--image2", help="a second image: prints the similarity of the largest faces")
    args = ap.parse_args()

    cfg = IdentityConfig.from_config(config.load_app_config().get("identity"))
    engine = build_face_engine(cfg.face, config.load_app_config().get("model", {}).get("device", "auto"))
    if engine is None:
        sys.exit("No face engine available (check the model files and your configuration)")
    print("engine:", engine.model_name, "| embedding size:", engine.dim)

    embeddings = []
    for path in [p for p in (args.image, args.image2) if p]:
        img = cv2.imread(path)
        if img is None:
            sys.exit(f"Cannot read {path}")
        t0 = time.perf_counter()
        faces = engine.detect(img)
        t1 = time.perf_counter()
        print(f"\n{path}: {len(faces)} face(s), detection {1000 * (t1 - t0):.1f} ms")
        for i, f in enumerate(faces):
            q = face_quality(img, f, cfg.face)
            print(f"  face {i}: size {f.width:.0f}x{f.height:.0f}  score {f.score:.2f}  "
                  f"yaw {q.yaw_ratio:+.2f}  sharpness {q.sharpness:.0f}  gate: {'ok' if q.ok else q.reason}")
        if faces:
            t2 = time.perf_counter()
            emb = engine.embed(img, faces[0])
            print(f"  embedding of the largest face: {len(emb)} values, {1000 * (time.perf_counter() - t2):.1f} ms")
            embeddings.append(emb)
    if len(embeddings) == 2:
        print(f"\ncosine similarity between the two largest faces: {cosine(*embeddings):.3f}")
        print("(compare with your thresholds only after running face_eval.py; one pair proves nothing)")


if __name__ == "__main__":
    main()
