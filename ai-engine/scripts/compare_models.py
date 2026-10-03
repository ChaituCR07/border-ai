import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

from app import config  # noqa: E402
from app.detection.classes import resolve_class_ids  # noqa: E402
from app.detection.inference import load_model, run_inference  # noqa: E402
from app.pipeline.visualizer import draw_detections  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def main():
    cfg = config.load_app_config()["model"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--models", nargs="+", default=["yolov8n.pt", "yolov8s.pt"])
    ap.add_argument("--frames", type=int, default=150)
    ap.add_argument("--sample-frame", type=int, default=60)
    args = ap.parse_args()

    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"Device: {device}\n")
    print(f"{'model':<14}{'infer ms':>10}{'p95 ms':>9}{'det/frame':>11}")

    out_dir = config.OUTPUT_DIR / "annotated"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in args.models:
        model = load_model(name)
        class_ids = resolve_class_ids(model.names, cfg["classes"])
        src = FileSource("CMP", args.video, realtime=False)
        if not src.open():
            sys.exit("Cannot open video")

        inf_ms, counts = [], []
        for i in range(args.frames):
            frame = src.read()
            if frame is None:
                break
            dets, speed = run_inference(model, frame.image, cfg["confidence"],
                                        cfg["iou"], cfg["image_size"], class_ids,
                                        cfg["device"], cfg.get("max_det", 300))
            inf_ms.append(speed["inference"])
            counts.append(len(dets))
            if i == args.sample_frame:
                cv2.imwrite(str(out_dir / f"cmp_{Path(name).stem}_{Path(args.video).stem}.jpg"),
                            draw_detections(frame.image.copy(), dets))
        src.release()

        print(f"{name:<14}{np.mean(inf_ms):>10.1f}{np.percentile(inf_ms, 95):>9.1f}"
              f"{np.mean(counts):>11.1f}")


if __name__ == "__main__":
    main()
