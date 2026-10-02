import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]

from ingestion.camera_manager import CameraManager  # noqa: E402

TILE_W, TILE_H = 640, 360


def overlay(frame, stats) -> np.ndarray:
    img = cv2.resize(frame.image, (TILE_W, TILE_H))
    ts = datetime.fromtimestamp(frame.timestamp, tz=timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    lines = [
        f"{frame.camera_id}  #{frame.frame_id}",
        f"{ts} UTC  {stats['fps']:.1f} FPS  drop {stats['dropped']}",
    ]
    for i, text in enumerate(lines):
        y = 22 + i * 22
        cv2.putText(img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
    return img


def no_signal(camera_id, status) -> np.ndarray:
    img = np.zeros((TILE_H, TILE_W, 3), np.uint8)
    cv2.putText(img, f"{camera_id}: NO SIGNAL ({status})", (20, TILE_H // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    return img


def grid(tiles, cols=2) -> np.ndarray:
    while len(tiles) % cols:
        tiles.append(np.zeros((TILE_H, TILE_W, 3), np.uint8))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    return np.vstack(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true",
                    help="no window; print stats and save one snapshot per camera")
    ap.add_argument("--seconds", type=int, default=0,
                    help="stop after N seconds (0 = until 'q' / Ctrl+C)")
    args = ap.parse_args()

    mgr = CameraManager.from_config(BASE_DIR / "configs" / "cameras.json", BASE_DIR)
    mgr.start_all()

    last_frames = {}
    started = time.time()
    last_print = 0.0
    try:
        while True:
            tiles = []
            stats = mgr.stats()
            for cid in mgr.camera_ids:
                f = mgr.get_frame(cid)
                if f is not None:
                    last_frames[cid] = f
                if cid in last_frames:
                    tiles.append(overlay(last_frames[cid], stats[cid]))
                else:
                    tiles.append(no_signal(cid, stats[cid]["status"]))

            if args.headless:
                if time.time() - last_print >= 1.0:
                    print(stats)
                    last_print = time.time()
            else:
                try:
                    cv2.imshow("border-ai | cameras", grid(tiles))
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
            snap_dir = BASE_DIR / "outputs" / "snapshots"
            snap_dir.mkdir(parents=True, exist_ok=True)
            for cid, f in last_frames.items():
                cv2.imwrite(str(snap_dir / f"{cid}_day2.jpg"), f.image)
        mgr.stop_all()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
