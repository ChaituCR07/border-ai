import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app import config  # noqa: E402
from app.detection.classes import resolve_class_ids  # noqa: E402
from app.detection.inference import load_model, run_inference  # noqa: E402
from app.pipeline.visualizer import draw_detections, put_text  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def summarize(name, values):
    arr = np.array(values)
    print(f"  {name:<14} mean {arr.mean():6.1f} ms   p95 {np.percentile(arr, 95):6.1f} ms")


def main():
    cfg = config.load_app_config()["model"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--model", default=cfg["name"])
    ap.add_argument("--conf", type=float, default=cfg["confidence"])
    ap.add_argument("--iou", type=float, default=cfg["iou"])
    ap.add_argument("--imgsz", type=int, default=cfg["image_size"])
    ap.add_argument("--fps", type=float, default=None, help="target FPS (frame skipping)")
    ap.add_argument("--width", type=int, default=None, help="resize width")
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args()

    src = FileSource("CLIP", args.video, target_fps=args.fps,
                     resize_width=args.width, realtime=False)
    if not src.open():
        sys.exit(f"Cannot open video: {args.video}")

    model = load_model(args.model)
    class_ids = resolve_class_ids(model.names, cfg["classes"])

    out_dir = config.OUTPUT_DIR / "annotated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{Path(args.video).stem}_day3.mp4"
    out_fps = args.fps or src.source_fps
    writer = None

    inference_ms, total_ms = [], []
    class_counts = Counter()
    frames = 0

    while True:
        frame = src.read()
        if frame is None:
            break

        t0 = time.perf_counter()
        dets, speed = run_inference(model, frame.image, args.conf, args.iou,
                                    args.imgsz, class_ids, cfg["device"],
                                    cfg.get("max_det", 300))
        annotated = draw_detections(frame.image, dets)
        put_text(annotated, f"frame {frame.frame_id}  det {len(dets)}", (10, 25))
        t1 = time.perf_counter()

        if writer is None:
            h, w = annotated.shape[:2]
            writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                                     out_fps, (w, h))
        writer.write(annotated)

        inference_ms.append(speed["inference"])
        total_ms.append((t1 - t0) * 1000)
        class_counts.update(d.class_name for d in dets)
        frames += 1
        if args.max_frames and frames >= args.max_frames:
            break

    src.release()
    if writer:
        writer.release()

    print(f"\nProcessed {frames} frames -> {out_path}")
    summarize("inference", inference_ms)
    summarize("detect+draw", total_ms)
    print(f"  effective speed: {1000 / np.mean(total_ms):.1f} FPS")
    print(f"  detections by class: {dict(class_counts)}")


if __name__ == "__main__":
    main()
