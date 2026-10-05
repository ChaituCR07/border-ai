import argparse
import itertools
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.tracking.manager import MultiCameraTracker  # noqa: E402
from app.tracking.metrics import summarize_tracks  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402
from ingestion.sources.file_source import FileSource  # noqa: E402


def replay(cached, min_conf, params, names, fps):
    tracker = MultiCameraTracker(names, params, default_fps=fps)
    for fd, ts in cached:
        filtered = replace(fd, detections=[d for d in fd.detections
                                           if d.confidence >= min_conf])
        tracker.update(filtered, timestamp=ts)
    return summarize_tracks(tracker.store("TUNE").all_tracks())


def main():
    cfg = config.load_app_config()
    base = TrackerParams.from_config(cfg["tracker"])

    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--det-conf", nargs="+", type=float, default=[0.25, 0.4])
    ap.add_argument("--high", nargs="+", type=float, default=[0.4, 0.5, 0.6])
    ap.add_argument("--match", nargs="+", type=float, default=[0.7, 0.8, 0.9])
    ap.add_argument("--buffer", nargs="+", type=int, default=[30, 60])
    args = ap.parse_args()

    src = FileSource("TUNE", args.video, target_fps=args.fps,
                     resize_width=args.width, realtime=False)
    if not src.open():
        sys.exit("Cannot open video")
    eff_fps = min(args.fps, src.source_fps) if args.fps else src.source_fps

    detector = Detector.from_config()
    floor = min(args.det_conf)

    print(f"Detecting once at conf {floor} and caching ...")
    cached = []
    while True:
        frame = src.read()
        if frame is None:
            break
        fd = detector.detect_frame(frame, conf=floor)
        cached.append((fd, frame.video_time_ms / 1000.0))
    src.release()
    print(f"{len(cached)} frames cached\n")

    rows = []
    for dconf, high, match, buf in itertools.product(
            args.det_conf, args.high, args.match, args.buffer):
        params = replace(base, track_high_thresh=high, match_thresh=match, track_buffer=buf,
                         new_track_thresh=max(high, base.new_track_thresh))
        s = replay(cached, dconf, params, detector.model.names, eff_fps)
        rows.append((dconf, high, match, buf, s))

    rows.sort(key=lambda r: (r[4]["fragment_candidates"], r[4]["short_tracks"], r[4]["tracks"]))

    print(f"{'det_conf':>8}{'high':>6}{'match':>7}{'buffer':>7}"
          f"{'tracks':>8}{'short':>7}{'frag':>6}{'median_s':>10}")
    for dconf, high, match, buf, s in rows:
        print(f"{dconf:>8}{high:>6}{match:>7}{buf:>7}"
              f"{s['tracks']:>8}{s['short_tracks']:>7}{s['fragment_candidates']:>6}"
              f"{s['median_duration_s']:>10}")


if __name__ == "__main__":
    main()
