import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app import config  # noqa: E402
from app.anpr.config import AnprConfig  # noqa: E402
from app.anpr.factory import build_ocr  # noqa: E402
from app.anpr.metrics import char_accuracy  # noqa: E402
from app.anpr.plate_format import PlateFormats, clean_text  # noqa: E402
from app.anpr.preprocess import preprocess  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="plate crops named TRUTH_xxx.jpg")
    ap.add_argument("--preprocess", nargs="+", default=["none", "gray", "clahe", "sharpen"])
    ap.add_argument("--heights", nargs="+", type=int, default=[96])
    ap.add_argument("--formats", nargs="+", default=["indian", "generic"])
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cfg = AnprConfig.from_config(config.load_app_config().get("anpr"))
    ocr = build_ocr(cfg)
    formats = PlateFormats(args.formats)

    files = sorted(p for p in Path(args.folder).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if args.limit:
        files = files[:args.limit]
    if not files:
        sys.exit("No images found")
    ocr.read(preprocess(cv2.imread(str(files[0])), "none"))                 # warm-up

    print(f"{len(files)} crops\n")
    print(f"{'preprocess':<10}{'height':>7}{'raw exact':>11}{'corrected exact':>17}"
          f"{'char acc':>10}{'mean conf':>11}{'ms/read':>9}")
    failures = {}
    for mode in args.preprocess:
        for height in args.heights:
            raw_ok = fixed_ok = 0
            chars, confs, ms = [], [], []
            for p in files:
                truth = p.stem.split("_")[0].upper()
                img = cv2.imread(str(p))
                if img is None:
                    continue
                t0 = time.perf_counter()
                res = ocr.read(preprocess(img, mode, height))
                ms.append((time.perf_counter() - t0) * 1000)
                raw_ok += clean_text(res.text) == truth
                corrected = formats.check(res.text).text
                fixed_ok += corrected == truth
                chars.append(char_accuracy(corrected, truth))
                confs.append(res.confidence)
                if corrected != truth:
                    failures.setdefault((mode, height), []).append((p.name, truth, corrected, res.confidence))
            n = len(files)
            print(f"{mode:<10}{height:>7}{raw_ok / n:>11.1%}{fixed_ok / n:>17.1%}"
                  f"{np.mean(chars):>10.1%}{np.mean(confs):>11.2f}{np.mean(ms):>9.1f}")

    key = next(iter(failures), None)
    if key:
        print(f"\nFirst failures for {key}:")
        for name, truth, pred, conf in failures[key][:15]:
            print(f"  {name:<28} truth {truth:<12} read {pred:<12} conf {conf:.2f}")


if __name__ == "__main__":
    main()
