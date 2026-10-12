import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.anpr.factory import build_anpr  # noqa: E402
from app.anpr.metrics import evaluate_records, format_report  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.pipeline.visualizer import draw_tracks, put_text  # noqa: E402
from app.tracking.manager import MultiCameraTracker  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def set_path(d: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--camera-id", default="CAM_002")
    ap.add_argument("--truth", help="docs/ground_truth/anpr_<clip>.json")
    ap.add_argument("--fps", type=float)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override an anpr setting, e.g. --set preprocess=gray --set schedule.ocr_every_n_frames=3")
    args = ap.parse_args()

    app_cfg = copy.deepcopy(config.load_app_config())
    for item in args.set:
        key, value = item.split("=", 1)
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass                                       # keep as a string
        set_path(app_cfg.setdefault("anpr", {}), key, value)

    params = TrackerParams.from_config(app_cfg["tracker"])
    detector = Detector.from_config()
    service = build_anpr(app_cfg)
    if service is None:
        sys.exit("ANPR is disabled in configs/app.yaml")

    stem = Path(args.video).stem
    out_dir = config.OUTPUT_DIR / "anpr" / stem
    service.attach(out_dir, block_when_full=True)      # no worker thread: we call run_pending()

    src = FileSource(args.camera_id, args.video, target_fps=args.fps,
                     resize_width=args.width, realtime=False)
    if not src.open():
        sys.exit(f"Cannot open {args.video}")
    eff_fps = min(args.fps, src.source_fps) if args.fps else src.source_fps
    tracker = MultiCameraTracker(detector.model.names, params, default_fps=eff_fps)

    writer, frames = None, 0
    t_start = time.perf_counter()
    while True:
        frame = src.read()
        if frame is None:
            break
        video_s = frame.video_time_ms / 1000.0                 # records use video seconds
        fd = detector.detect_frame(frame, conf=params.detection_conf)
        ft, upd = tracker.update(fd, timestamp=video_s)

        service.submit(args.camera_id, ft, frame.image)
        service.on_tracks_removed(args.camera_id, upd.removed)
        service.run_pending()

        if not args.no_video:
            image = draw_tracks(frame.image, ft.tracks, tracker.store(args.camera_id),
                                extra_labels=service.plates_snapshot(args.camera_id))
            put_text(image, f"{video_s:6.1f}s", (10, 25))
            if writer is None:
                h, w = image.shape[:2]
                writer = cv2.VideoWriter(str(out_dir / f"{stem}_anpr.mp4"),
                                         cv2.VideoWriter_fourcc(*"mp4v"), eff_fps, (w, h))
            writer.write(image)
        frames += 1
        if args.max_frames and frames >= args.max_frames:
            break

    src.release()
    if writer:
        writer.release()
    service.stop(drain=True)
    elapsed = time.perf_counter() - t_start

    records = service.all_records()
    print(f"\n{frames} frames in {elapsed:.1f} s | {len(records)} vehicles with a plate record")
    print(f"{'vehicle':>8} {'class':<11}{'plate':<13}{'conf':>6}{'reads':>6}{'votes':>6}"
          f"{'agree':>7} {'format':<8}{'seen (s)':>14}")
    for r in sorted(records, key=lambda r: r.first_seen):
        print(f"{r.track_id:>8} {r.vehicle_class:<11}{r.plate:<13}{r.confidence:>6.2f}{r.reads:>6}"
              f"{r.votes:>6}{r.agreement:>7.2f} {r.format_level:<8}{r.first_seen:>6.1f}-{r.last_seen:<6.1f}")
    print("\nANPR counters:", service.status())
    print("Stage timings (ms):", {k: v["mean_all_ms"] for k, v in service.timers.summary().items()})

    if args.truth:
        truth = json.load(open(args.truth))["plates"]
        print("\n" + format_report(evaluate_records(records, truth)))

    with open(out_dir / "records.json", "w") as f:
        json.dump([r.to_dict() for r in records], f, indent=2)


if __name__ == "__main__":
    main()
