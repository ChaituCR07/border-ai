import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app.schemas.detection import Detection, FrameDetections  # noqa: E402
from app.tracking.manager import MultiCameraTracker  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402


def generate_synthetic_frame(frame_id: int, num_objects: int, width: int = 1280, height: int = 720):
    dets = []
    for obj_i in range(num_objects):
        # Linear movement across horizontal axis
        base_x = (obj_i * 120 + frame_id * 6) % (width - 80)
        base_y = (100 + obj_i * 50) % (height - 150)
        dets.append(Detection(
            class_id=0,
            class_name="person",
            confidence=0.88 + 0.1 * np.sin(frame_id * 0.1),
            x1=float(base_x),
            y1=float(base_y),
            x2=float(base_x + 50),
            y2=float(base_y + 120),
        ))
    return FrameDetections(
        camera_id="BENCH_CAM",
        frame_id=frame_id,
        timestamp=float(frame_id / 30.0),
        width=width,
        height=height,
        detections=dets,
    )


def main():
    parser = argparse.ArgumentParser(description="Benchmark ByteTrack & TrackStore overhead across object densities")
    parser.add_argument("--densities", nargs="+", type=int, default=[1, 5, 10, 25, 50],
                        help="Number of objects per frame to test")
    parser.add_argument("--frames", type=int, default=150, help="Number of frames per test")
    parser.add_argument("--warmup", type=int, default=15, help="Warmup iterations")
    args = parser.parse_args()

    print(f"\nRunning Tracking Benchmark ({args.frames} frames, warmup={args.warmup})")
    header = f"{'Objects':>10}{'Mean (ms)':>12}{'P95 (ms)':>12}{'Throughput (FPS)':>18}{'Tracks Active':>16}"
    print(header)
    print("-" * len(header))

    params = TrackerParams()
    class_names = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

    for n_objs in args.densities:
        tracker = MultiCameraTracker(class_names, params, default_fps=30.0)

        # Warmup
        for f_idx in range(args.warmup):
            fd = generate_synthetic_frame(f_idx, n_objs)
            tracker.update(fd)

        # Timed benchmark
        times_ms = []
        for f_idx in range(args.warmup, args.warmup + args.frames):
            fd = generate_synthetic_frame(f_idx, n_objs)
            t0 = time.perf_counter()
            ft, upd = tracker.update(fd)
            dt = (time.perf_counter() - t0) * 1000.0
            times_ms.append(dt)

        arr = np.array(times_ms)
        mean_ms = float(arr.mean())
        p95_ms = float(np.percentile(arr, 95))
        fps = 1000.0 / max(mean_ms, 0.001)
        active_count = len(tracker.store("BENCH_CAM").active_tracks())

        print(f"{n_objs:>10}{mean_ms:>12.3f}{p95_ms:>12.3f}{fps:>18.1f}{active_count:>16}")


if __name__ == "__main__":
    main()
