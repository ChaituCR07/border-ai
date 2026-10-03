import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.detection.classes import resolve_class_ids  # noqa: E402
from app.detection.inference import load_model, run_inference  # noqa: E402
from app.pipeline.visualizer import draw_detections  # noqa: E402


def main():
    cfg = config.load_app_config()["model"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--model", default=cfg["name"])
    ap.add_argument("--conf", type=float, default=cfg["confidence"])
    ap.add_argument("--iou", type=float, default=cfg["iou"])
    ap.add_argument("--imgsz", type=int, default=cfg["image_size"])
    ap.add_argument("--all-classes", action="store_true",
                    help="disable the class filter to see everything the model detects")
    args = ap.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        sys.exit(f"Cannot read image: {args.image}")

    model = load_model(args.model)
    class_ids = None if args.all_classes else resolve_class_ids(model.names, cfg["classes"])

    dets, speed = run_inference(model, image, args.conf, args.iou, args.imgsz,
                                class_ids, cfg["device"], cfg.get("max_det", 300))

    print(f"{len(dets)} detections | preprocess {speed['preprocess']:.1f} ms, "
          f"inference {speed['inference']:.1f} ms, postprocess {speed['postprocess']:.1f} ms")
    for d in sorted(dets, key=lambda x: -x.confidence):
        print(f"  {d.class_name:<11} {d.confidence:.2f}  "
              f"box=({d.x1:.0f},{d.y1:.0f},{d.x2:.0f},{d.y2:.0f})")

    out_dir = config.OUTPUT_DIR / "annotated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{Path(args.image).stem}_det.jpg"
    cv2.imwrite(str(out), draw_detections(image, dets))
    print("Saved", out)


if __name__ == "__main__":
    main()
