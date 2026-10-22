import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.analytics.engine import RuleEngine  # noqa: E402
from app.detection.detector import Detector  # noqa: E402
from app.pipeline.pipeline import Pipeline  # noqa: E402
from app.pipeline.visualizer import make_grid  # noqa: E402
from app.tracking.tracker import TrackerParams  # noqa: E402
from app.anpr.factory import build_anpr  # noqa: E402
from app.watchlist.factory import build_watchlist  # noqa: E402
from app.identity.factory import build_identity  # noqa: E402
from app.behaviour.factory import build_behaviour  # noqa: E402
from app.threat.factory import build_scorer
from app.events.factory import build_publisher  # noqa: E402
from app.behaviour.timeutil import get_zone, parse_clock_start  # noqa: E402
from ingestion.camera_manager import (CameraConfig, CameraManager, build_source,  # noqa: E402
                                      load_camera_configs)

TILE = (640, 360)


def build_configs(args):
    if args.source:                                   # quick single-source mode
        is_rtsp = args.source.lower().startswith("rtsp://")
        source = args.source if is_rtsp else str(Path(args.source).resolve())
        cfgs = [CameraConfig(camera_id=args.camera_id, name=args.camera_id,
                             source_type="rtsp" if is_rtsp else "file", source=source,
                             target_fps=args.fps, resize_width=args.width,
                             loop=False, realtime=False)]
    else:
        cfgs = [c for c in load_camera_configs(config.CONFIG_DIR / "cameras.json") if c.enabled]

    if args.only:
        cfgs = [c for c in cfgs if c.camera_id in args.only]
    if not cfgs:
        sys.exit("No cameras selected")
    if args.fps:
        cfgs = [replace(c, target_fps=args.fps) for c in cfgs]

    all_files = all(c.source_type == "file" for c in cfgs)
    mode = args.mode or ("live" if args.loop else ("offline" if all_files else "live"))
    if mode == "offline" and not all_files:
        sys.exit("Offline mode needs video files. Use --mode live for RTSP sources.")

    adjusted = []
    for c in cfgs:
        if c.source_type == "file":
            if mode == "offline":
                c = replace(c, loop=False, realtime=False)        # process once, as fast as possible
            else:
                c = replace(c, realtime=True, loop=c.loop or args.loop)   # behave like a camera
        adjusted.append(c)
    return adjusted, mode


def format_status(st: dict) -> str:
    lines = []
    for cid, c in st["cameras"].items():
        lines.append(f"  {cid:<8} src={str(c['source_status']):<12} ingest {c['ingest_fps']} | "
                     f"proc {c['proc_fps']} | out {c['out_fps']} FPS | "
                     f"drops in {c['ingest_dropped']} out {c['output_dropped']} | "
                     f"tracks {c['tracks_active']} | events {c['events']} | "
                     f"processed {c['processed']}")
    stages = st["stages"]

    def m(key):
        return f"{stages[key]['mean_ms']:.1f}" if key in stages else "-"

    lines.append(f"  stages (ms): detect/frame {m('detect_ms_per_frame')} | track {m('track_ms')} | "
                 f"rules {m('rules_ms')} | render {m('render_ms')} | write {m('write_ms')} | "
                 f"latency {m('latency_ms')} | avg batch {st['avg_batch_size']}")
    a = st.get("anpr")
    if a:
        lines.append("  anpr: " + " | ".join(f"{k} {v}" for k, v in a.items()))
    w = st.get("watchlist")
    if w:
        lines.append("  watchlist: " + " | ".join(f"{k} {v}" for k, v in w.items()))
    i = st.get("identity")
    if i:
        lines.append("  identity: " + " | ".join(f"{k} {v}" for k, v in i.items()))
    b = st.get("behaviour")
    if b:
        lines.append("  behaviour: " + " | ".join(f"{k} {v}" for k, v in b.items()))
    t = st.get("scoring")
    if t:
        lines.append("  scoring: " + " | ".join(f"{k} {v}" for k, v in t.items()))
    b = st.get("events_bus")
    if b:
        lines.append("  event bus: " + " | ".join(f"{k} {v}" for k, v in b.items()))
    p = st.get("process") or {}
    if p:
        lines.append("  process: " + " | ".join(f"{k} {v}" for k, v in p.items()))
    return "\n".join(lines)


def wait(pipeline, every: float) -> None:
    last = time.time()
    while not pipeline.finished():
        time.sleep(0.25)
        if every and time.time() - last >= every:
            print(format_status(pipeline.status()) + "\n")
            last = time.time()


def show(pipeline) -> None:
    """Display window. OpenCV windows must live on the main thread."""
    while not pipeline.finished():
        tiles = []
        for cid in pipeline.camera_ids:
            img = pipeline.hub.latest_image(cid)
            tiles.append(cv2.resize(img, TILE) if img is not None else None)
        try:
            cv2.imshow("border-ai | pipeline", make_grid(tiles, 2, TILE))
            if cv2.waitKey(30) & 0xFF == ord("q"):
                break
        except cv2.error:
            print("No display available. Run without --show.")
            wait(pipeline, 5)
            break
    cv2.destroyAllWindows()


def serve(pipeline, args) -> None:
    import uvicorn
    from app.main import app
    app.state.pipeline = pipeline                     # the API reuses this pipeline and its detector
    print(f"Serving on http://{args.host}:{args.port}   "
          f"(/pipeline/status, /events/recent, /snapshot/<camera>, /stream/<camera>, /docs)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


def main():
    ap = argparse.ArgumentParser(description="border-ai end-to-end pipeline")
    ap.add_argument("--source", help="a video file or rtsp:// URL (otherwise configs/cameras.json)")
    ap.add_argument("--camera-id", default="CAM_001", help="camera id for --source (selects the zones file)")
    ap.add_argument("--only", nargs="+", help="only these camera ids from cameras.json")
    ap.add_argument("--mode", choices=["offline", "live"],
                    help="offline: files as fast as possible, nothing dropped. live: paced, latency bounded")
    ap.add_argument("--fps", type=float, help="override target FPS for all cameras")
    ap.add_argument("--width", type=int, default=1280, help="resize width for --source")
    ap.add_argument("--loop", action="store_true", help="loop file sources in live mode")
    ap.add_argument("--seconds", type=float, default=0, help="stop after N seconds")
    ap.add_argument("--max-frames", type=int, default=0, help="stop each camera after N frames")
    ap.add_argument("--no-anpr", action="store_true", help="disable plate recognition")
    ap.add_argument("--no-watchlist", action="store_true", help="disable watchlist matching")
    ap.add_argument("--identity", action="store_true",
                    help="enable face matching and person Re-ID (consenting subjects only)")
    ap.add_argument("--rules", help="rules file (default configs/rules.json)")
    ap.add_argument("--no-behaviour", action="store_true", help="disable the behaviour engine")
    ap.add_argument("--no-scoring", action="store_true", help="disable threat scoring")
    ap.add_argument("--no-snapshots", action="store_true", help="do not save evidence frames for alerts")
    ap.add_argument("--publish", action="store_true", help="publish events to Redis Streams")
    ap.add_argument("--clock-start", help="simulated start time for offline clips, e.g. 2026-10-12T02:13:00 "
                                          "(read in the site time zone unless it has an offset)")
    ap.add_argument("--no-video", action="store_true", help="do not write annotated MP4s")
    ap.add_argument("--log-tracks", action="store_true", help="also write per-frame tracks.jsonl")
    ap.add_argument("--half", action="store_true", help="FP16 (GPU only)")
    ap.add_argument("--show", action="store_true", help="show a live grid window")
    ap.add_argument("--serve", action="store_true", help="start the API with MJPEG streams")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--stats-every", type=float, default=5.0)
    args = ap.parse_args()

    cfgs, mode = build_configs(args)
    mgr = CameraManager([build_source(c, config.BASE_DIR) for c in cfgs])
    app_cfg = config.load_app_config()
    params = TrackerParams.from_config(app_cfg["tracker"])
    anpr = None if args.no_anpr else build_anpr(app_cfg)
    watchlist = None if args.no_watchlist else build_watchlist(app_cfg)
    identity = build_identity(app_cfg, watchlist, force=args.identity)
    detector = Detector.from_config(**({"half": True} if args.half else {}))
    rules = RuleEngine(config.CONFIG_DIR / "zones")

    behaviour = None if args.no_behaviour else build_behaviour(args.rules)
    scorer = None if args.no_scoring else build_scorer(args.rules)
    publisher = build_publisher(app_cfg, force=args.publish)
    clock_start = None
    if args.clock_start:
        if mode != "offline":
            print("note: --clock-start applies to offline file runs only; live sources use the real clock")
        else:
            tz = get_zone(behaviour.cfg.timezone) if behaviour else get_zone("UTC")
            clock_start = parse_clock_start(args.clock_start, tz)

    pipeline = Pipeline(
        detector, mgr, params, rules, config.OUTPUT_DIR / "runs",
        camera_fps={c.camera_id: c.target_fps for c in cfgs if c.target_fps},
        write_video=not args.no_video, log_tracks=args.log_tracks,
        offline=(mode == "offline"), max_seconds=args.seconds, max_frames=args.max_frames,
        anpr=anpr, watchlist=watchlist, identity=identity,
        behaviour=behaviour, clock_start=clock_start, scorer=scorer, save_snapshots=not args.no_snapshots, publisher=publisher)

    print(f"Run {pipeline.run_id} | mode {mode} | cameras {pipeline.camera_ids}\n"
          f"Output: {pipeline.run_dir}\n")
    pipeline.start()
    try:
        if args.serve:
            serve(pipeline, args)
        elif args.show:
            show(pipeline)
        else:
            wait(pipeline, args.stats_every)
    except KeyboardInterrupt:
        print("\nStopping ...")
    finally:
        pipeline.stop()
        print("\n=== Final status ===")
        print(format_status(pipeline.status()))
        print(f"\nRun folder: {pipeline.run_dir}")


if __name__ == "__main__":
    main()
