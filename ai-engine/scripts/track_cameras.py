import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.pipeline.visualizer import draw_tracks, make_grid, put_text  # noqa: E402
from app.tracking.manager import MultiCameraTracker  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402
from ingestion.camera_manager import CameraManager, FpsCounter, load_camera_configs  # noqa: E402

TILE = (640, 360)


def main():
    cfg = config.load_app_config()
    params = TrackerParams.from_config(cfg["tracker"])

    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--seconds", type=int, default=0)
    ap.add_argument("--jsonl", action="store_true")
    ap.add_argument("--log-events", action="store_true",
                    help="print track lifecycle events")
    args = ap.parse_args()

    cam_cfg_path = config.BASE_DIR / "configs" / "cameras.json"
    camera_fps = {c.camera_id: (c.target_fps or 15.0)
                  for c in load_camera_configs(cam_cfg_path) if c.enabled}

    detector = Detector.from_config()
    tracker = MultiCameraTracker(detector.model.names, params, camera_fps=camera_fps)
    mgr = CameraManager.from_config(cam_cfg_path, config.BASE_DIR)
    mgr.start_all()

    jsonl = None
    if args.jsonl:
        ev = config.OUTPUT_DIR / "events"
        ev.mkdir(parents=True, exist_ok=True)
        jsonl = open(ev / "tracks_day5.jsonl", "w")

    fps = {cid: FpsCounter() for cid in mgr.camera_ids}
    last = {}                       # camera_id -> (annotated image, frame_id)
    started, last_print = time.time(), 0.0

    try:
        while True:
            stats = mgr.stats()

            # One frame per camera per cycle keeps each camera's frames in order
            frames = []
            for cid in mgr.camera_ids:
                f = mgr.get_frame(cid, timeout=0.005)
                if f is not None:
                    frames.append(f)

            if frames:
                results = detector.detect_frames(frames, conf=params.detection_conf)
                for f, fd in zip(frames, results):
                    ft, upd = tracker.update(fd)                 # wall-clock timestamps (live)
                    store = tracker.store(f.camera_id)
                    last[f.camera_id] = (draw_tracks(f.image, ft.tracks, store), f.frame_id)
                    fps[f.camera_id].tick()

                    if jsonl:
                        jsonl.write(json.dumps(ft.to_dict()) + "\n")
                    if args.log_events:
                        for t in upd.new:
                            print(f"[{f.camera_id}] NEW {t.track_id}")
                        for t in upd.removed:
                            print(f"[{f.camera_id}] REMOVED {t.track_id} "
                                  f"({t.dominant_class}, {t.duration_s:.1f}s, {t.hits} hits)")
            else:
                time.sleep(0.002)

            tiles = []
            for cid in mgr.camera_ids:
                if cid in last:
                    img, fid = last[cid]
                    store = tracker.store(cid)
                    tile = cv2.resize(img, TILE)
                    put_text(tile, f"{cid} #{fid}  active {len(store.active_tracks())} "
                                   f"lost {len(store.lost_tracks())}  "
                                   f"{fps[cid].fps:.1f} FPS  drop {stats[cid]['dropped']}",
                             (8, 22))
                    tiles.append(tile)
                else:
                    tiles.append(None)

            if args.headless:
                if time.time() - last_print >= 1.0:
                    print({cid: (round(fps[cid].fps, 1), len(tracker.store(cid).active_tracks()))
                           for cid in mgr.camera_ids}, "(FPS, active tracks)")
                    last_print = time.time()
            else:
                try:
                    cv2.imshow("border-ai | tracking", make_grid(tiles, 2, TILE))
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
            for cid, (img, _) in last.items():
                cv2.imwrite(str(snap / f"{cid}_day5_tracks.jpg"), img)
        mgr.stop_all()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
