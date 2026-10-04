import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.pipeline.visualizer import draw_detections, make_grid, put_text  # noqa: E402
from ingestion.camera_manager import CameraManager, FpsCounter  # noqa: E402

TILE = (640, 360)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--seconds", type=int, default=0)
    ap.add_argument("--jsonl", action="store_true",
                    help="write every FrameDetections as JSON to outputs/events/")
    ap.add_argument("--half", action="store_true", help="force FP16 (GPU only)")
    args = ap.parse_args()

    overrides = {"half": True} if args.half else {}
    detector = Detector.from_config(**overrides)
    print("Detector:", detector.info())

    mgr = CameraManager.from_config(config.BASE_DIR / "configs" / "cameras.json",
                                    config.BASE_DIR)
    mgr.start_all()

    jsonl = None
    if args.jsonl:
        events_dir = config.OUTPUT_DIR / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        jsonl = open(events_dir / "detections_day4.jsonl", "w")

    det_fps = {cid: FpsCounter() for cid in mgr.camera_ids}
    last = {}                  # camera_id -> (annotated image, n_detections, frame_id)
    batch_sizes = []
    started, last_print = time.time(), 0.0

    try:
        while True:
            stats = mgr.stats()

            # Dynamic batching: take whatever each camera has ready right now
            frames = []
            for cid in mgr.camera_ids:
                f = mgr.get_frame(cid, timeout=0.005)
                if f is not None:
                    frames.append(f)

            if frames:
                results = detector.detect_frames(frames)
                batch_sizes.append(len(frames))
                for f, r in zip(frames, results):
                    last[f.camera_id] = (draw_detections(f.image, r.detections),
                                         len(r.detections), f.frame_id)
                    det_fps[f.camera_id].tick()
                    if jsonl:
                        jsonl.write(json.dumps(r.to_dict()) + "\n")
            else:
                time.sleep(0.002)

            tiles = []
            for cid in mgr.camera_ids:
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
                    avg_batch = sum(batch_sizes[-50:]) / max(len(batch_sizes[-50:]), 1)
                    print({cid: round(det_fps[cid].fps, 1) for cid in mgr.camera_ids},
                          f"avg batch {avg_batch:.1f}",
                          f"model {detector.avg_ms_per_frame:.1f} ms/frame",
                          {cid: stats[cid]["dropped"] for cid in mgr.camera_ids})
                    last_print = time.time()
            else:
                try:
                    cv2.imshow("border-ai | detection (batched)", make_grid(tiles, 2, TILE))
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
        if jsonl:
            jsonl.close()
        if args.headless:
            snap = config.OUTPUT_DIR / "snapshots"
            snap.mkdir(parents=True, exist_ok=True)
            for cid, (img, _, _) in last.items():
                cv2.imwrite(str(snap / f"{cid}_day4_det.jpg"), img)
        mgr.stop_all()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
