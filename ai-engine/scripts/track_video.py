import argparse
import csv
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app import config  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.pipeline.visualizer import draw_tracks, put_text  # noqa: E402
from app.tracking.manager import MultiCameraTracker  # noqa: E402
from app.tracking.metrics import summarize_tracks  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def main():
    cfg = config.load_app_config()
    params = TrackerParams.from_config(cfg["tracker"])

    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--fps", type=float, default=None, help="target FPS (frame skipping)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--no-trails", action="store_true")
    args = ap.parse_args()

    src = FileSource("CLIP", args.video, target_fps=args.fps,
                     resize_width=args.width, realtime=False)
    if not src.open():
        sys.exit(f"Cannot open video: {args.video}")
    eff_fps = min(args.fps, src.source_fps) if args.fps else src.source_fps

    detector = Detector.from_config()
    tracker = MultiCameraTracker(detector.model.names, params, default_fps=eff_fps)
    print(f"Clip {Path(args.video).name}: {eff_fps:.1f} FPS | detector {detector.model_name} "
          f"| detection_conf {params.detection_conf} | max lost frames "
          f"{params.max_lost_frames(eff_fps)}")

    stem = Path(args.video).stem
    out_dir = config.OUTPUT_DIR / "annotated"
    ev_dir = config.OUTPUT_DIR / "events"
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}_tracked_day5.mp4"
    writer = None

    track_ms, total_ms = [], []
    lifecycle = Counter()
    frames = 0

    while True:
        frame = src.read()
        if frame is None:
            break
        t0 = time.perf_counter()

        fd = detector.detect_frame(frame, conf=params.detection_conf)

        t1 = time.perf_counter()
        # Offline analysis uses VIDEO time, so durations are real seconds
        ft, upd = tracker.update(fd, timestamp=frame.video_time_ms / 1000.0)
        track_ms.append((time.perf_counter() - t1) * 1000)

        store = tracker.store("CLIP")
        annotated = draw_tracks(frame.image, ft.tracks, store, show_trails=not args.no_trails)
        put_text(annotated, f"frame {frame.frame_id}  active {len(store.active_tracks())}  "
                            f"lost {len(store.lost_tracks())}", (10, 25))
        total_ms.append((time.perf_counter() - t0) * 1000)

        lifecycle.update(new=len(upd.new), lost=len(upd.lost),
                         reactivated=len(upd.reactivated), removed=len(upd.removed))

        if writer is None:
            h, w = annotated.shape[:2]
            writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                                     eff_fps, (w, h))
        writer.write(annotated)

        frames += 1
        if args.max_frames and frames >= args.max_frames:
            break

    src.release()
    if writer:
        writer.release()

    tracks = tracker.store("CLIP").all_tracks()
    csv_path = ev_dir / f"tracks_{stem}.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["track_id", "class", "first_s", "last_s", "duration_s", "hits",
                    "state", "displacement_px"])
        for t in sorted(tracks, key=lambda x: x.first_seen):
            w.writerow([t.track_id, t.dominant_class, round(t.first_seen, 2),
                        round(t.last_seen, 2), round(t.duration_s, 2), t.hits,
                        t.state, round(t.displacement_px, 1)])

    print(f"\nProcessed {frames} frames -> {out_path}")
    print(f"Track table -> {csv_path}")
    print("Summary:", summarize_tracks(tracks))
    print("By class:", dict(Counter(t.dominant_class for t in tracks)))
    print("Lifecycle events:", dict(lifecycle))
    print(f"Tracker overhead: {np.mean(track_ms):.2f} ms/frame (mean) | "
          f"detect+track+draw: {np.mean(total_ms):.1f} ms/frame")


if __name__ == "__main__":
    main()
