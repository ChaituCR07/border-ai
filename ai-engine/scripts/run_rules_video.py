import argparse
import json
import sys
import time
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app import config  # noqa: E402
from app.analytics.engine import RuleEngine  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.pipeline.visualizer import (FlashState, draw_event_feed, draw_lines,  # noqa: E402
                                     draw_tracks, draw_zones, put_text)
from app.tracking.manager import MultiCameraTracker  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def event_key(e) -> str:
    key = f"{e.type}:{e.rule_id}"
    if e.direction:
        key += f":{e.direction}"
    return key


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


def check_expected(counts: Counter, path: str, tolerance: int) -> bool:
    with open(path) as f:
        expected = json.load(f)["expected"]
    ok = True
    print(f"\n{'event':<32}{'expected':>9}{'got':>6}  result")
    for key in sorted(set(expected) | set(counts)):
        exp, got = expected.get(key, 0), counts.get(key, 0)
        passed = abs(got - exp) <= tolerance
        ok &= passed
        print(f"{key:<32}{exp:>9}{got:>6}  {'PASS' if passed else 'FAIL'}")
    return ok


def main():
    cfg = config.load_app_config()
    params = TrackerParams.from_config(cfg["tracker"])

    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--camera", default="CAM_001", help="selects configs/zones/<camera>.json")
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--expect", default=None, help="ground-truth JSON to compare against")
    ap.add_argument("--tolerance", type=int, default=0)
    args = ap.parse_args()

    src = FileSource(args.camera, args.video, target_fps=args.fps,
                     resize_width=args.width, realtime=False)
    if not src.open():
        sys.exit(f"Cannot open video: {args.video}")
    eff_fps = min(args.fps, src.source_fps) if args.fps else src.source_fps

    detector = Detector.from_config()
    tracker = MultiCameraTracker(detector.model.names, params, default_fps=eff_fps)
    rules = RuleEngine(config.CONFIG_DIR / "zones")
    flash = FlashState()
    feed = deque(maxlen=50)

    stem = Path(args.video).stem
    out_dir, ev_dir = config.OUTPUT_DIR / "annotated", config.OUTPUT_DIR / "events"
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}_rules_day6.mp4"
    jsonl = open(ev_dir / f"events_{stem}.jsonl", "w")
    writer = None

    t_base = time.time()                     # offline clips: wall-clock base + video time
    counts, rule_ms, n_frames = Counter(), [], 0

    while True:
        frame = src.read()
        if frame is None:
            break
        video_s = frame.video_time_ms / 1000.0
        ts = t_base + video_s

        fd = detector.detect_frame(frame, conf=params.detection_conf)
        ft, upd = tracker.update(fd, timestamp=ts)
        store = tracker.store(args.camera)

        t0 = time.perf_counter()
        events = rules.update(ft, upd, store)
        rule_ms.append((time.perf_counter() - t0) * 1000)

        for e in events:
            e.details["video_time_s"] = round(video_s, 2)
            counts[event_key(e)] += 1
            jsonl.write(json.dumps(e.to_dict()) + "\n")
            who = f"{e.object_class} #{e.track_id}"
            feed.append(f"{mmss(video_s)} {e.type} {e.rule_name} {e.direction or ''} {who}")
            print(f"[{mmss(video_s)}] {e.type:<14} {e.rule_id:<4} {who:<14} "
                  f"{e.direction or ''} {e.details.get('reason', '')}")
        flash.trigger(events, ts)

        stats = rules.stats(args.camera)
        image = frame.image
        draw_zones(image, rules.rules_for(args.camera), stats["zone_occupancy"], flash, ts)
        draw_lines(image, rules.rules_for(args.camera), stats["line_counts"], flash, ts)
        draw_tracks(image, ft.tracks, store)
        put_text(image, f"{mmss(video_s)}  frame {frame.frame_id}  "
                        f"events {sum(counts.values())}", (10, 25))
        draw_event_feed(image, feed)

        if writer is None:
            hh, ww = image.shape[:2]
            writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                                     eff_fps, (ww, hh))
        writer.write(image)
        n_frames += 1

    src.release()
    jsonl.close()
    if writer:
        writer.release()

    print(f"\nProcessed {n_frames} frames -> {out_path}")
    print(f"Events -> {ev_dir / f'events_{stem}.jsonl'}")
    print("Event counts:", dict(counts))
    print(f"Rule engine overhead: {np.mean(rule_ms):.3f} ms/frame (mean)")

    if args.expect:
        sys.exit(0 if check_expected(counts, args.expect, args.tolerance) else 1)


if __name__ == "__main__":
    main()
