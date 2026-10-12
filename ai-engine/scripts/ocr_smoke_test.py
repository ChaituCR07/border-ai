import argparse
import sys
import time
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app.anpr.ocr import PaddleOcrEngine  # noqa: E402


def synthetic_plate(text: str) -> np.ndarray:
    img = np.full((110, 520, 3), 255, np.uint8)
    cv2.rectangle(img, (4, 4), (515, 105), (0, 0, 0), 4)
    cv2.putText(img, text, (22, 78), cv2.FONT_HERSHEY_DUPLEX, 2.6, (0, 0, 0), 5, cv2.LINE_AA)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", help="optional real plate crop to read instead")
    ap.add_argument("--device", default="cpu", help="cpu | gpu:0")
    ap.add_argument("--runs", type=int, default=10)
    args = ap.parse_args()

    print("paddleocr", version("paddleocr"), "| paddlepaddle", version("paddlepaddle"))
    t0 = time.perf_counter()
    engine = PaddleOcrEngine(lang="en", device=args.device)
    print(f"engine loaded in {time.perf_counter() - t0:.1f} s")

    img = cv2.imread(args.image) if args.image else synthetic_plate("KA01AB1234")
    if img is None:
        sys.exit("Cannot read image")

    first = engine.read(img)
    print("first read (includes warm-up):", first.text, round(first.confidence, 3))

    times = []
    for _ in range(args.runs):
        t = time.perf_counter()
        res = engine.read(img)
        times.append((time.perf_counter() - t) * 1000)
    print(f"read: {res.text!r} conf {res.confidence:.3f} | "
          f"{np.mean(times):.1f} ms mean, {np.percentile(times, 95):.1f} ms p95 over {args.runs} runs")
    print("lines:", res.lines)


if __name__ == "__main__":
    main()
