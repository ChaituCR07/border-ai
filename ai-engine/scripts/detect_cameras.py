import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.detection.classes import resolve_class_ids  # noqa: E402
from app.detection.inference import load_model, run_inference  # noqa: E402
from app.pipeline.visualizer import draw_detections, make_grid, put_text  # noqa: E402
from ingestion.camera_manager import CameraManager, FpsCounter  # noqa: E402

TILE = (640, 360)


def main():
    cfg = config.load_app_config()["model"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--seconds", type=int, default=0)
    args = ap.parse_args()

    model = load_model(cfg["name"])
    class_ids = resolve_class_ids(model.names, cfg["classes"])

    mgr = CameraManager.from_config(config.BASE_DIR / "configs" / "cameras.json",
                                    config.BASE_DIR)
    mgr.start_all()

    det_fps = {cid: FpsCounter() for cid in mgr.camera_ids}
    last = {}                      # camera_id -> (annotated image, n_detections, frame_id)
    started, last_print = time.time(), 0.0

    try:
        while True:
            stats = mgr.stats()
            tiles = []
            for cid in mgr.camera_ids:
                frame = mgr.get_frame(cid, timeout=0.01)
                if frame is not None:
                    dets, _ = run_inference(model, frame.image, cfg["confidence"],
                                            cfg["iou"], cfg["image_size"], class_ids,
                                            cfg["device"], cfg.get("max_det", 300))
                    last[cid] = (draw_detections(frame.image, dets),
                                 len(dets), frame.frame_id)
                    det_fps[cid].tick()

                if cid in last:
                    img, n, fid = last[cid]
                    tile = cv2.resize(img, TILE)
                    put_text(tile, f"{cid} #{fid}  det {n}  "
                                   f"{det_fps[cid].fps:.1f} FPS  "
                                   f"drop {stats[cid]['dropped']}", (8, 22))
                    tiles.append(tile)
                else:
                    tiles.append(None)

            if args.headless:
                if time.time() - last_print >= 1.0:
                    print({cid: (round(det_fps[cid].fps, 1), stats[cid]["dropped"])
                           for cid in mgr.camera_ids}, "(det FPS, dropped)")
                    last_print = time.time()
            else:
                try:
                    cv2.imshow("border-ai | detection", make_grid(tiles, 2, TILE))
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                except cv2.error:
                    print("No display available. Re-run with --headless.")
                    break

            if args.seconds and time.time() - started > args.seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if args.headless:
            snap = config.OUTPUT_DIR / "snapshots"
            snap.mkdir(parents=True, exist_ok=True)
            for cid, (img, _, _) in last.items():
                cv2.imwrite(str(snap / f"{cid}_day3_det.jpg"), img)
        mgr.stop_all()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
