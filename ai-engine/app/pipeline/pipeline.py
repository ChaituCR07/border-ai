import json
import logging
import platform
import queue
import re
import subprocess
import threading
import time
from collections import Counter, deque
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app import config
from app.analytics.engine import RuleEngine
from app.pipeline.metrics import StageTimer
from app.pipeline.queues import put_blocking, put_drop_oldest
from app.pipeline.renderer import FrameRenderer
from app.pipeline.sinks import FrameHub, JsonlSink, VideoSink
from app.pipeline.types import FrameResult
from app.schemas.events import Event
from app.tracking.manager import MultiCameraTracker
from app.tracking.tracker import TrackerParams
from ingestion.camera_manager import CameraManager, FpsCounter
from ingestion.sources.file_source import FileSource

log = logging.getLogger("pipeline")

_URL_CREDS = re.compile(r"(://)[^/@\s]+@")


def mask_url(url: str) -> str:
    """Hide user:password in RTSP URLs before writing them anywhere."""
    return _URL_CREDS.sub(r"***@", url)


def event_key(e: Event) -> str:
    key = f"{e.type}:{e.rule_id}"
    return f"{key}:{e.direction}" if e.direction else key


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, timeout=3, cwd=str(config.BASE_DIR))
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


class Pipeline:
    """Camera frames -> batched detection -> per-camera tracking -> rules -> annotated
    output. See the architecture diagram in the Day 7 notes."""

    def __init__(self, detector, manager: CameraManager, tracker_params: TrackerParams,
                 rules: RuleEngine, output_dir: Path, *,
                 camera_fps: Optional[Dict[str, float]] = None,
                 write_video: bool = True, log_tracks: bool = False,
                 offline: Optional[bool] = None, jpeg_quality: int = 80,
                 out_queue_size: int = 8, max_seconds: float = 0, max_frames: int = 0):
        self.detector = detector
        self.mgr = manager
        self.params = tracker_params
        self.rules = rules
        self.write_video = write_video
        self.max_seconds = max_seconds
        self.max_frames = max_frames
        self.camera_ids: List[str] = list(manager.camera_ids)

        self.offline = offline if offline is not None else all(
            isinstance(w.source, FileSource) and not w.source.realtime
            for w in manager.workers.values())

        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(output_dir) / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.tracker = MultiCameraTracker(detector.model.names, tracker_params,
                                          default_fps=15.0,
                                          camera_fps=dict(camera_fps or {}))
        self.events = JsonlSink(self.run_dir / "events.jsonl")
        self.tracks_log = JsonlSink(self.run_dir / "tracks.jsonl") if log_tracks else None
        self.hub = FrameHub(jpeg_quality)
        self.timers = StageTimer()

        # Load and validate every camera's rules NOW, so bad config fails at startup
        self._rules_cfg = {cid: rules.rules_for(cid) for cid in self.camera_ids}

        self._out_queues = {cid: queue.Queue(maxsize=out_queue_size) for cid in self.camera_ids}
        self._out_threads: Dict[str, threading.Thread] = {}
        self._video_sinks: Dict[str, VideoSink] = {}
        self.counters = {cid: {"processed": 0, "rendered": 0, "out_dropped": 0, "events": 0}
                         for cid in self.camera_ids}
        self._proc_fps = {cid: FpsCounter() for cid in self.camera_ids}
        self._out_fps = {cid: FpsCounter() for cid in self.camera_ids}
        self._active = {cid: 0 for cid in self.camera_ids}
        self._last_ft: Dict[str, object] = {}
        self._last_video_s: Dict[str, Optional[float]] = {}
        self._event_counts: Counter = Counter()
        self._batch_sizes: deque = deque(maxlen=300)

        self._stop = threading.Event()
        self._infer_thread: Optional[threading.Thread] = None
        self.state = "created"
        self.started_at = 0.0
        self.finished_at = 0.0

        self._proc = None
        try:
            import psutil
            self._proc = psutil.Process()
            self._proc.cpu_percent(None)
        except ImportError:
            pass

    # ------------------------------------------------------------------ lifecycle
    @property
    def stopped(self) -> bool:
        return self._stop.is_set() or self.state == "finished"

    def finished(self) -> bool:
        return self.state == "finished"

    def start(self) -> None:
        self._write_manifest()
        for cid in self.camera_ids:
            t = threading.Thread(target=self._output_loop, args=(cid,),
                                 name=f"out-{cid}", daemon=True)
            self._out_threads[cid] = t
            t.start()
        self.mgr.start_all()
        self.started_at = time.time()
        self.state = "running"
        self._infer_thread = threading.Thread(target=self._infer_loop,
                                              name="pipeline-infer", daemon=True)
        self._infer_thread.start()

    def stop(self, timeout: Optional[float] = 60) -> bool:
        self._stop.set()
        return self.join(timeout)

    def join(self, timeout: Optional[float] = None) -> bool:
        if self._infer_thread is None:
            return True
        self._infer_thread.join(timeout)
        return not self._infer_thread.is_alive()

    # ------------------------------------------------------------------ inference thread
    def _infer_loop(self) -> None:
        t_base = time.time()
        try:
            while not self._stop.is_set():
                if self.max_seconds and time.time() - self.started_at > self.max_seconds:
                    break

                batch = []
                for cid in self.camera_ids:           # at most one frame per camera per cycle
                    if self.max_frames and self.counters[cid]["processed"] >= self.max_frames:
                        continue
                    f = self.mgr.get_frame(cid, timeout=0.003)
                    if f is not None:
                        batch.append(f)

                if not batch:
                    if self._all_finished():
                        break
                    continue                          # get_frame timeouts already throttle

                self._process_batch(batch, t_base)
        except Exception:
            log.exception("Inference loop crashed")
        finally:
            self._flush_rules()
            self._close_outputs()
            self.mgr.stop_all()
            self._finalize()

    def _all_finished(self) -> bool:
        if self.max_frames and all(self.counters[c]["processed"] >= self.max_frames
                                   for c in self.camera_ids):
            return True
        for w in self.mgr.workers.values():
            if w.status not in ("ended", "failed") or not w.frames.empty():
                return False
        return True

    def _clock(self, cid: str, frame, t_base: float):
        """Offline files: video time on a wall-clock base. Live/paced: the frame's wall-clock time."""
        src = self.mgr.workers[cid].source
        if isinstance(src, FileSource) and not src.realtime:
            video_s = frame.video_time_ms / 1000.0
            return video_s, t_base + video_s
        return None, frame.timestamp

    def _effective_fps(self, cid: str, frame) -> float:
        native = frame.source_fps or 15.0
        target = self.mgr.workers[cid].source.target_fps
        return min(target, native) if target else native

    def _process_batch(self, batch, t_base: float) -> None:
        t0 = time.perf_counter()
        results = self.detector.detect_frames(batch, conf=self.params.detection_conf)
        self.timers.record("detect_ms_per_frame", (time.perf_counter() - t0) * 1000 / len(batch))
        self._batch_sizes.append(len(batch))

        for f, fd in zip(batch, results):
            cid = f.camera_id
            self.tracker.camera_fps.setdefault(cid, self._effective_fps(cid, f))
            video_s, ts = self._clock(cid, f, t_base)

            t1 = time.perf_counter()
            ft, upd = self.tracker.update(fd, timestamp=ts)
            store = self.tracker.store(cid)
            t2 = time.perf_counter()
            events = self.rules.update(ft, upd, store)
            t3 = time.perf_counter()
            self.timers.record("track_ms", (t2 - t1) * 1000)
            self.timers.record("rules_ms", (t3 - t2) * 1000)

            self._emit_events(cid, events, video_s)
            if self.tracks_log:
                self.tracks_log.write(ft.to_dict())

            n_active = len(store.active_tracks())
            res = FrameResult(frame=f, ft=ft, events=events, store=store.snapshot(),
                              rule_stats=self.rules.stats(cid), video_s=video_s,
                              n_active=n_active, n_lost=len(store.lost_tracks()))
            self._enqueue(cid, res)

            self.counters[cid]["processed"] += 1
            self._proc_fps[cid].tick()
            self._active[cid] = n_active
            self._last_ft[cid] = ft
            self._last_video_s[cid] = video_s

    def _emit_events(self, cid: str, events: List[Event], video_s: Optional[float]) -> None:
        for e in events:
            if video_s is not None:
                e.details["video_time_s"] = round(video_s, 2)
            self.events.write(e.to_dict())
            self._event_counts[event_key(e)] += 1
        self.counters[cid]["events"] += len(events)

    def _enqueue(self, cid: str, res: FrameResult) -> None:
        q = self._out_queues[cid]
        if self.offline:
            put_blocking(q, res, self._stop)         # backpressure: never lose a frame
        elif put_drop_oldest(q, res):                # live: keep latency bounded
            self.counters[cid]["out_dropped"] += 1

    def _flush_rules(self) -> None:
        """Close zone presences still open when the stream ends (EXIT, reason stream_ended)."""
        for cid, ft in self._last_ft.items():
            try:
                events = self.rules.flush(cid, ft, self.tracker.store(cid))
                self._emit_events(cid, events, self._last_video_s.get(cid))
            except Exception:
                log.exception("Flush failed for %s", cid)

    # ------------------------------------------------------------------ output threads
    def _output_loop(self, cid: str) -> None:
        q = self._out_queues[cid]
        renderer = FrameRenderer(cid, self._rules_cfg[cid])
        sink: Optional[VideoSink] = None
        while True:
            res = q.get()
            if res is None:
                break
            try:
                t0 = time.perf_counter()
                image = renderer.render(res, self._out_fps[cid].fps)
                t1 = time.perf_counter()
                if self.write_video:
                    if sink is None:
                        fps = self.tracker.camera_fps.get(cid, 15.0)
                        sink = VideoSink(self.run_dir / f"annotated_{cid}.mp4", fps)
                        self._video_sinks[cid] = sink
                    sink.write(image)
                t2 = time.perf_counter()

                self.hub.put(cid, image)
                self._out_fps[cid].tick()
                self.counters[cid]["rendered"] += 1
                self.timers.record("render_ms", (t1 - t0) * 1000)
                self.timers.record("write_ms", (t2 - t1) * 1000)
                if not self.offline:
                    self.timers.record("latency_ms", (time.time() - res.frame.timestamp) * 1000)
            except Exception:
                log.exception("Output error for %s", cid)
        if sink is not None:
            sink.close()

    def _close_outputs(self) -> None:
        for cid, q in self._out_queues.items():
            try:
                q.put(None, timeout=10)              # sentinel; frames ahead of it are still written
            except queue.Full:
                log.warning("Output queue for %s did not drain in time", cid)
        for t in self._out_threads.values():
            t.join(timeout=30)

    def _finalize(self) -> None:
        self.finished_at = time.time()
        self.events.close()
        if self.tracks_log:
            self.tracks_log.close()
        try:
            summary = self.status()
            summary["event_counts"] = dict(self._event_counts)
            summary["duration_s"] = round(self.finished_at - self.started_at, 1)
            (self.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        except Exception:
            log.exception("Could not write summary")
        self.state = "finished"

    # ------------------------------------------------------------------ reporting
    def status(self) -> dict:
        stats = self.mgr.stats()
        cams = {}
        for cid in self.camera_ids:
            c, s = self.counters[cid], stats.get(cid, {})
            cams[cid] = {
                "source_status": s.get("status"),
                "ingest_fps": s.get("fps"),
                "proc_fps": round(self._proc_fps[cid].fps, 1),
                "out_fps": round(self._out_fps[cid].fps, 1),
                "ingest_dropped": s.get("dropped"),
                "output_dropped": c["out_dropped"],
                "processed": c["processed"],
                "rendered": c["rendered"],
                "events": c["events"],
                "tracks_active": self._active[cid],
                "out_queue": self._out_queues[cid].qsize(),
            }

        process = {}
        if self._proc is not None:
            process = {"rss_mb": round(self._proc.memory_info().rss / 1024 ** 2, 1),
                       "cpu_percent": self._proc.cpu_percent(None),
                       "threads": self._proc.num_threads()}
        try:
            import torch
            if torch.cuda.is_available():
                process["gpu_mem_mb"] = round(torch.cuda.memory_allocated() / 1024 ** 2, 1)
        except Exception:
            pass

        batches = list(self._batch_sizes)
        end = self.finished_at or time.time()
        return {
            "state": self.state,
            "mode": "offline" if self.offline else "live",
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "uptime_s": round(end - self.started_at, 1) if self.started_at else 0.0,
            "cameras": cams,
            "stages": self.timers.summary(),
            "avg_batch_size": round(sum(batches) / len(batches), 2) if batches else 0.0,
            "events_total": self.events.count,
            "detector": self.detector.info(),
            "process": process,
        }

    def _write_manifest(self) -> None:
        try:
            import torch
            import ultralytics
            versions = {"torch": torch.__version__, "ultralytics": ultralytics.__version__,
                        "cuda": torch.cuda.is_available()}
        except Exception:
            versions = {}
        cameras = {}
        for cid, w in self.mgr.workers.items():
            src = w.source
            cameras[cid] = {
                "type": type(src).__name__,
                "source": mask_url(str(getattr(src, "url", getattr(src, "path", "")))),
                "target_fps": src.target_fps,
                "resize_width": src.resize_width,
            }
        manifest = {
            "run_id": self.run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "mode": "offline" if self.offline else "live",
            "git_commit": _git_commit(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": versions,
            "detector": self.detector.info(),
            "tracker": asdict(self.params),
            "cameras": cameras,
            "rules": {cid: asdict(r) for cid, r in self._rules_cfg.items()},
        }
        (self.run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
