import argparse
import gc
import itertools
import platform
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from app import config  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def hardware_name() -> str:
    if torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return platform.processor() or platform.machine() or "CPU"


def load_frames(video: str, count: int, width: int):
    src = FileSource("BENCH", video, resize_width=width, realtime=False)
    if not src.open():
        sys.exit(f"Cannot open video: {video}")
    frames = []
    while len(frames) < count:
        f = src.read()
        if f is None:
            break
        frames.append(f.image)
    src.release()
    if not frames:
        sys.exit("No frames read")
    return frames


def main():
    cfg = config.load_app_config()["model"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--models", nargs="+", default=["yolov8n.pt", "yolov8s.pt"])
    ap.add_argument("--imgsz", nargs="+", type=int, default=[640, 960])
    ap.add_argument("--half", nargs="+", type=int, choices=[0, 1], default=[0, 1])
    ap.add_argument("--batch", nargs="+", type=int, default=[1, 3])
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--width", type=int, default=1280,
                    help="resize width, matching the pipeline's cameras.json")
    ap.add_argument("--target-fps", type=float, default=15.0)
    ap.add_argument("--append", action="store_true",
                    help="append result rows to docs/benchmarks.md")
    args = ap.parse_args()

    frames = load_frames(args.video, args.frames, args.width)
    hw = hardware_name()
    clip = Path(args.video).name
    print(f"Hardware: {hw} | clip: {clip} | frames: {len(frames)} | "
          f"frame size: {frames[0].shape[1]}x{frames[0].shape[0]}\n")

    header = (f"{'model':<12}{'imgsz':>6}{'fp16':>6}{'batch':>6}{'ms/frame':>10}"
              f"{'p95':>8}{'FPS':>8}{'det/frm':>9}{'VRAM MB':>9}{'cams@fps':>10}")
    print(header)
    print("-" * len(header))

    md_rows = []
    for model_name, imgsz, half, batch in itertools.product(
            args.models, args.imgsz, args.half, args.batch):

        if half and not torch.cuda.is_available():
            print(f"{model_name:<12}{imgsz:>6}{half:>6}{batch:>6}   skipped (FP16 needs a GPU)")
            continue

        det = Detector(model_name=model_name, conf=cfg["confidence"], iou=cfg["iou"],
                       imgsz=imgsz, classes=cfg["classes"],
                       device=cfg.get("device", "auto"), half=bool(half),
                       max_det=cfg.get("max_det", 300))

        for _ in range(args.warmup):
            det.detect_batch(frames[:batch])
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        import time
        per_frame_ms, det_counts = [], []
        for i in range(0, len(frames) - batch + 1, batch):
            chunk = frames[i:i + batch]
            t0 = time.perf_counter()
            results = det.detect_batch(chunk)          # includes CUDA sync
            dt = (time.perf_counter() - t0) * 1000
            per_frame_ms.append(dt / batch)
            det_counts.extend(len(r) for r in results)

        arr = np.array(per_frame_ms)
        mean_ms, p95_ms = float(arr.mean()), float(np.percentile(arr, 95))
        fps = 1000.0 / mean_ms
        vram = (torch.cuda.max_memory_allocated() / 1024 ** 2
                if torch.cuda.is_available() else 0.0)
        cams = int(fps // args.target_fps)
        mean_det = float(np.mean(det_counts))

        print(f"{model_name:<12}{imgsz:>6}{half:>6}{batch:>6}{mean_ms:>10.1f}"
              f"{p95_ms:>8.1f}{fps:>8.1f}{mean_det:>9.1f}{vram:>9.0f}{cams:>10}")

        note = (f"{'FP16' if half else 'FP32'}, batch {batch}, {clip}, "
                f"{mean_det:.1f} det/frame, ~{cams} cams @ {args.target_fps:.0f} FPS")
        md_rows.append(f"| {date.today()} | {hw} | {model_name} | {imgsz} | {batch} | "
                       f"{mean_ms:.1f} | {fps:.1f} | {note} |")

        del det
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print("\nMarkdown rows for docs/benchmarks.md:\n")
    print("\n".join(md_rows))

    if args.append and md_rows:
        path = config.BASE_DIR / "docs" / "benchmarks.md"
        with open(path, "a") as f:
            f.write("\n".join(md_rows) + "\n")
        print(f"\nAppended {len(md_rows)} rows to {path}")


if __name__ == "__main__":
    main()
