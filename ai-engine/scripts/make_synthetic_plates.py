import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

STATES = ["KA", "MH", "TN", "DL", "AP", "KL", "GJ", "UP", "RJ", "WB"]
SERIES = "ABCDEFGHJKLMNPRSTUVWXYZ"        # real series skip I, O, Q


def random_plate(rng: random.Random) -> str:
    series = "".join(rng.choice(SERIES) for _ in range(rng.randint(1, 3)))
    return f"{rng.choice(STATES)}{rng.randint(1, 99):02d}{series}{rng.randint(1, 9999):04d}"


def render(text: str, rng: random.Random, hard: bool) -> np.ndarray:
    bg = (255, 255, 255) if rng.random() < 0.7 else (40, 210, 255)      # white or yellow (BGR)
    img = np.full((110, 520, 3), bg, np.uint8)
    cv2.rectangle(img, (4, 4), (515, 105), (0, 0, 0), 4)
    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 2.6, 5)
    cv2.putText(img, text, (max(8, (520 - tw) // 2), 78), cv2.FONT_HERSHEY_DUPLEX,
                2.6, (0, 0, 0), 5, cv2.LINE_AA)

    # geometry
    angle = rng.uniform(-5, 5) * (1.5 if hard else 1.0)
    m = cv2.getRotationMatrix2D((260, 55), angle, 1.0)
    img = cv2.warpAffine(img, m, (520, 110), borderMode=cv2.BORDER_REPLICATE)

    # resolution loss
    w = rng.randint(70, 140) if hard else rng.randint(140, 260)
    small = cv2.resize(img, (w, int(w * 110 / 520)), interpolation=cv2.INTER_AREA)
    img = cv2.resize(small, (520, 110), interpolation=cv2.INTER_LINEAR)

    # blur, noise, brightness
    k = rng.choice([1, 3, 5, 7] if hard else [1, 1, 3])
    if k > 1:
        img = cv2.GaussianBlur(img, (k, k), 0)
    noise = np.random.default_rng(rng.randint(0, 10 ** 6)).normal(0, 12 if hard else 5, img.shape)
    img = np.clip(img.astype(np.float32) * rng.uniform(0.6, 1.2) + noise, 0, 255).astype(np.uint8)

    # JPEG artifacts
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(25, 60) if hard else rng.randint(60, 95)])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/plates/synthetic")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--hard", action="store_true", help="stronger degradation")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(args.count):
        text = random_plate(rng)
        cv2.imwrite(str(out / f"{text}_{i:03d}.jpg"), render(text, rng, args.hard))
    print(f"Wrote {args.count} plates to {out}")


if __name__ == "__main__":
    main()
