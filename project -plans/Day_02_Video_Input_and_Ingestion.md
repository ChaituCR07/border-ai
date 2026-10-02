# Day 2: Video Input and Ingestion

**Project:** AI-Based Intelligent Video Analytics Platform for Border Surveillance (`border-ai`)
**Week 1 goal:** Video → Detection → Tracking → Zone/Line Analysis → Annotated Video
**Day 2 goal:** Reliable multi-camera frame input from video files and RTSP streams, with every frame carrying `camera_id`, `frame_id`, and `timestamp`, so Day 3's detector has a clean, stable source to consume.

> Timebox: one day. Today is about **getting frames in reliably**. No YOLO, no tracking, no zones. The only "analytics" today is an overlay of camera ID, frame ID, FPS, and time.

**Working branch:** `feature/detection` (merge to `develop` at end of day).

---

## 1. Suggested Time Plan

| Block | Task | Est. time |
|---|---|---|
| 1 | Collect and inspect test videos | 45 min |
| 2 | Package setup + `Frame` dataclass + `VideoSource` base | 45 min |
| 3 | `FileSource` (frame skip, resize, pacing, loop, EOF) | 60 min |
| 4 | RTSP simulator + `RtspSource` (latest-frame reader, reconnect) | 90 min |
| 5 | `CameraManager` + per-camera workers + config loading | 75 min |
| 6 | Multi-camera viewer script with overlay | 45 min |
| 7 | ONVIF stub | 15 min |
| 8 | Tests, verification, commit | 45 min |

---

## 2. Prerequisites (from Day 1)

- Repo structure, `.venv`, Docker (Postgres + Redis), and `configs/` exist.
- `pip install -r video-ingestion/requirements.txt` already done (OpenCV, NumPy, python-dotenv, PyYAML).
- You can run `docker run` (needed for the RTSP simulator).
- **FFmpeg CLI installed** on the host (`ffmpeg -version`). Install if missing:
  - Ubuntu / WSL: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: install a build from ffmpeg.org and add it to PATH, or use WSL.

---

## 3. Task 1: Collect and Inspect Test Videos

### 3.1 What to collect (3 to 5 clips)

| File | Content | Why you need it |
|---|---|---|
| `person_walking.mp4` | A person or people walking across a scene | Detection, tracking, and line-crossing tests (Days 3-6) |
| `vehicles.mp4` | Cars, trucks, motorcycles on a road | Vehicle detection and later ANPR |
| `night.mp4` | Night or low-light / IR footage | Shows detection failure modes |
| `crowded.mp4` | Many overlapping people or vehicles | Occlusion and ID-switch tests on Day 5 |
| `rtsp_source.mp4` (optional) | Any clip to loop through the RTSP simulator | RTSP testing today |

Place them in `datasets/videos/` (gitignored). **Use only footage you are permitted to use** (open datasets, your own recordings, or clips with a license that allows it). Record the source and license of each clip in `datasets/README.md`.

Rename the Day 1 placeholder `sample_01.mp4` to match, or update `cameras.json` accordingly.

### 3.2 Inspect each clip

Write down resolution, FPS, duration, and codec. Use `ffprobe`:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,duration \
  -of default=noprint_wrappers=1 datasets/videos/person_walking.mp4
```

Or with OpenCV:

```bash
python -c "import cv2; c=cv2.VideoCapture('datasets/videos/person_walking.mp4'); print(c.get(3), c.get(4), c.get(5), c.get(7))"
```

(width, height, fps, frame count)

Record the results in a table at the bottom of `datasets/README.md`:

| File | Resolution | FPS | Duration | Codec | Source / license |
|---|---|---|---|---|---|

### 3.3 Optional: normalize problem clips

If a clip has an odd codec, variable frame rate, or huge resolution, create a normalized copy:

```bash
ffmpeg -i input.mp4 -c:v libx264 -preset fast -crf 23 -r 25 -an datasets/videos/clip_norm.mp4
```

**Deliverable:** 3-5 clips in `datasets/videos/` with a metadata table.

---

## 4. Task 2: Package Setup, Frame Model, and Source Interface

### 4.1 Make `ingestion` an installable package

So that `ai-engine` can `import ingestion` on Day 3, create `video-ingestion/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "ingestion"
version = "0.1.0"
dependencies = ["opencv-python", "numpy", "python-dotenv", "pyyaml"]

[tool.setuptools.packages.find]
include = ["ingestion*"]
```

Install in editable mode from the repo root (venv active):

```bash
pip install -e video-ingestion
```

Verify: `python -c "import ingestion; print(ingestion.__file__)"`

### 4.2 `video-ingestion/ingestion/__init__.py`

Set the FFmpeg capture options **before** OpenCV opens any stream. This must happen before the first `cv2.VideoCapture` is created.

```python
import os

# Force TCP for RTSP (more reliable than UDP), keep latency low,
# and time out stuck connections (microseconds; 5 s).
# If your FFmpeg build rejects "stimeout", try "timeout;5000000" instead.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|stimeout;5000000",
)
```

### 4.3 `ingestion/frame.py`

```python
from dataclasses import dataclass
import numpy as np


@dataclass
class Frame:
    camera_id: str
    frame_id: int            # increments per emitted frame, per camera
    timestamp: float         # wall-clock UTC epoch seconds when the frame was read
    video_time_ms: float     # position in the video file (0.0 for live streams)
    image: np.ndarray        # BGR image (H, W, 3)
    source_fps: float        # native FPS reported by the source

    @property
    def height(self) -> int:
        return self.image.shape[0]

    @property
    def width(self) -> int:
        return self.image.shape[1]
```

### 4.4 Timestamp convention (decide once, document in `docs/decisions/`)

- `timestamp` = **wall-clock UTC epoch seconds at the moment the frame was read**. All events (zone entries, line crossings, ANPR reads) will use this, for files and live streams alike. This keeps your event timeline consistent across cameras.
- `video_time_ms` = position inside a video file. Useful for debugging and for jumping to the right spot when you replay a clip. It is `0.0` for live streams.
- Convert to ISO 8601 UTC only at the output boundary (JSON, DB). Never store local-time strings.

Create `docs/decisions/0002-timestamp-convention.md` with these three lines.

### 4.5 `ingestion/sources/base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
import time

import cv2

from ..frame import Frame


def resize_keep_aspect(image, width: Optional[int]):
    """Downscale to `width` keeping aspect ratio. Never upscales."""
    if width is None:
        return image
    h, w = image.shape[:2]
    if w <= width:
        return image
    scale = width / w
    return cv2.resize(image, (width, int(h * scale)), interpolation=cv2.INTER_AREA)


class VideoSource(ABC):
    """Common interface for file and live sources."""

    def __init__(self, camera_id: str, target_fps: Optional[float] = None,
                 resize_width: Optional[int] = None):
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.resize_width = resize_width
        self.source_fps: float = 0.0
        self._frame_counter = 0

    # --- lifecycle ---
    @abstractmethod
    def open(self) -> bool: ...

    @abstractmethod
    def read(self) -> Optional[Frame]:
        """Return the next Frame, or None if no frame is available right now."""

    @abstractmethod
    def release(self) -> None: ...

    # --- state ---
    @property
    @abstractmethod
    def is_live(self) -> bool: ...

    @property
    def ended(self) -> bool:
        """True only for finite sources (files) once the end is reached."""
        return False

    @property
    def connected(self) -> bool:
        return True

    # --- helpers ---
    def _make_frame(self, image, video_time_ms: float = 0.0,
                    timestamp: Optional[float] = None) -> Frame:
        image = resize_keep_aspect(image, self.resize_width)
        self._frame_counter += 1
        return Frame(
            camera_id=self.camera_id,
            frame_id=self._frame_counter,
            timestamp=timestamp if timestamp is not None else time.time(),
            video_time_ms=video_time_ms,
            image=image,
            source_fps=self.source_fps,
        )
```

**Deliverable:** `Frame`, `VideoSource`, package installed, timestamp decision documented.

---

## 5. Task 3: `FileSource`

`ingestion/sources/file_source.py`

```python
import time
from pathlib import Path
from typing import Optional

import cv2

from .base import VideoSource
from ..frame import Frame


class FileSource(VideoSource):
    """Reads a video file as if it were a camera.

    realtime=True  -> paces output to target_fps (or the file's native FPS)
    realtime=False -> reads as fast as possible (useful for benchmarks and tests)
    loop=True      -> restarts at the end so a short clip behaves like a live feed
    """

    def __init__(self, camera_id: str, path, target_fps: Optional[float] = None,
                 resize_width: Optional[int] = None, loop: bool = False,
                 realtime: bool = True):
        super().__init__(camera_id, target_fps, resize_width)
        self.path = Path(path)
        self.loop = loop
        self.realtime = realtime
        self.cap: Optional[cv2.VideoCapture] = None
        self._step = 1
        self._ended = False
        self._next_deadline: Optional[float] = None

    @property
    def is_live(self) -> bool:
        return False

    @property
    def ended(self) -> bool:
        return self._ended

    def open(self) -> bool:
        if not self.path.exists():
            return False
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            return False
        self.source_fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        # Frame skipping: e.g. a 30 FPS file with target_fps=10 -> keep every 3rd frame
        if self.target_fps and self.target_fps < self.source_fps:
            self._step = max(1, round(self.source_fps / self.target_fps))
        self._ended = False
        return True

    def read(self) -> Optional[Frame]:
        if self.cap is None or self._ended:
            return None

        # Skip (step - 1) frames cheaply with grab(), which avoids a full decode-to-array
        for _ in range(self._step - 1):
            if not self.cap.grab():
                return self._on_end()

        ok, image = self.cap.read()
        if not ok:
            return self._on_end()

        video_time_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        self._pace()
        return self._make_frame(image, video_time_ms=video_time_ms)

    def _on_end(self) -> Optional[Frame]:
        if self.loop:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, image = self.cap.read()
            if ok:  # guard: an unreadable file must not loop forever
                self._pace()
                return self._make_frame(image, video_time_ms=0.0)
        self._ended = True
        return None

    def _pace(self) -> None:
        if not self.realtime:
            return
        effective_fps = self.target_fps or self.source_fps
        interval = 1.0 / effective_fps
        now = time.monotonic()
        if self._next_deadline is None:
            self._next_deadline = now
        if self._next_deadline > now:
            time.sleep(self._next_deadline - now)
        self._next_deadline = max(self._next_deadline, now) + interval

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
```

### Features delivered

- Frame skipping to a target FPS
- Resize with preserved aspect ratio (zones use normalized coordinates, so resizing is safe)
- Real-time pacing so a file behaves like a live camera (and a fast mode for benchmarks)
- Looping for short clips
- Clean end-of-file handling via the `ended` flag

**Deliverable:** `FileSource` passes the tests in Section 11.

---

## 6. Task 4: RTSP Simulator and `RtspSource`

### 6.1 Set up a local RTSP simulator (no physical camera needed)

**Terminal A: start MediaMTX (RTSP server):**

```bash
docker run --rm -it --name mediamtx -p 8554:8554 bluenviron/mediamtx:latest
```

**Terminal B: push a looping video into it as `cam3`:**

```bash
ffmpeg -re -stream_loop -1 -i datasets/videos/vehicles.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p -an \
  -f rtsp -rtsp_transport tcp rtsp://localhost:8554/cam3
```

**Terminal C: sanity check with ffplay or VLC:**

```bash
ffplay -rtsp_transport tcp rtsp://localhost:8554/cam3
```

You can run more streams (`cam4`, ...) with more `ffmpeg` commands. To simulate a **dropout**, stop the `ffmpeg` command and restart it later. Your reconnect logic must survive that.

**Note:** if Docker runs in a VM or WSL, `localhost` normally still works for published ports. If not, use the host IP.

### 6.2 `ingestion/sources/rtsp_source.py`

The key design: a **background reader thread** that decodes continuously and keeps **only the latest frame**. `read()` hands out the newest frame it has not yet returned. This prevents OpenCV's internal buffer from making you process stale video (the number one RTSP problem).

```python
import logging
import threading
import time
from typing import Optional

import cv2

from .base import VideoSource
from ..frame import Frame

log = logging.getLogger("ingestion.rtsp")


class RtspSource(VideoSource):
    def __init__(self, camera_id: str, url: str, target_fps: Optional[float] = None,
                 resize_width: Optional[int] = None,
                 reconnect_initial: float = 1.0, reconnect_max: float = 30.0):
        super().__init__(camera_id, target_fps, resize_width)
        self.url = url
        self.reconnect_initial = reconnect_initial
        self.reconnect_max = reconnect_max

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._latest = None          # newest decoded image
        self._latest_ts = 0.0        # wall-clock time it was decoded
        self._seq = 0                # increments per decoded frame
        self._last_returned_seq = 0
        self._connected = False
        self._last_emit = 0.0
        self._min_interval = (1.0 / target_fps) if target_fps else 0.0

    @property
    def is_live(self) -> bool:
        return True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_frame_age(self) -> float:
        """Seconds since the last decoded frame (large value = stream is stuck)."""
        return time.time() - self._latest_ts if self._latest_ts else float("inf")

    def open(self) -> bool:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._reader_loop, daemon=True, name=f"rtsp-{self.camera_id}")
        self._thread.start()
        return True  # connection happens (and retries) in the background

    def _reader_loop(self) -> None:
        backoff = self.reconnect_initial
        while not self._stop.is_set():
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                self._connected = False
                log.warning("[%s] cannot open stream, retrying in %.1fs",
                            self.camera_id, backoff)
                cap.release()
                self._stop.wait(backoff)
                backoff = min(backoff * 2, self.reconnect_max)
                continue

            log.info("[%s] stream connected", self.camera_id)
            backoff = self.reconnect_initial
            self._connected = True
            self.source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

            while not self._stop.is_set():
                ok, image = cap.read()
                if not ok:
                    break
                with self._lock:
                    self._latest = image
                    self._latest_ts = time.time()
                    self._seq += 1

            cap.release()
            self._connected = False
            if not self._stop.is_set():
                log.warning("[%s] stream lost, reconnecting in %.1fs",
                            self.camera_id, backoff)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, self.reconnect_max)

    def read(self) -> Optional[Frame]:
        # Throttle BEFORE consuming, so skipped frames are simply never handed out
        now = time.monotonic()
        if self._min_interval and (now - self._last_emit) < self._min_interval:
            return None

        with self._lock:
            if self._latest is None or self._seq == self._last_returned_seq:
                return None
            image = self._latest
            ts = self._latest_ts
            self._last_returned_seq = self._seq

        self._last_emit = now
        return self._make_frame(image, video_time_ms=0.0, timestamp=ts)

    def release(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)  # cap.read() can block; thread is a daemon
            self._thread = None
```

### 6.3 Behaviors to confirm manually

1. Start the stream, start your reader: frames arrive, `connected` is `True`.
2. Stop `ffmpeg`: within seconds `connected` becomes `False` and warnings show growing backoff (1s, 2s, 4s, ...).
3. Restart `ffmpeg`: the source reconnects on its own with no restart of your program.
4. Start with the stream **not running at all**: the program must start, log retries, and connect once the stream appears.
5. Latency: compare the stream's burned-in clock (or wave your hand in front of a webcam stream) with your viewer. It should lag by well under a second, not grow over time.

**Deliverable:** `RtspSource` survives dropouts and never serves stale, buffered video.

---

## 7. Task 5: `CameraManager`

### 7.1 Extend `configs/cameras.json`

```json
{
  "cameras": [
    {
      "camera_id": "CAM_001",
      "name": "North Gate",
      "source_type": "file",
      "source": "datasets/videos/person_walking.mp4",
      "target_fps": 15,
      "resize_width": 1280,
      "loop": true,
      "realtime": true,
      "enabled": true
    },
    {
      "camera_id": "CAM_002",
      "name": "East Road",
      "source_type": "file",
      "source": "datasets/videos/vehicles.mp4",
      "target_fps": 15,
      "resize_width": 1280,
      "loop": true,
      "realtime": true,
      "enabled": true
    },
    {
      "camera_id": "CAM_003",
      "name": "South Perimeter (RTSP)",
      "source_type": "rtsp",
      "source": "rtsp://localhost:8554/cam3",
      "target_fps": 15,
      "resize_width": 1280,
      "enabled": true
    }
  ]
}
```

Rules:

- File paths are **relative to the repo root** (resolved with `BASE_DIR`).
- Real camera URLs often contain credentials. Never commit those. Use an environment variable reference in the config, for example `"source": "${RTSP_CAM_003_URL}"`, and define `RTSP_CAM_003_URL` in `.env`. The loader below expands it.
- `enabled: false` lets you switch a camera off without deleting it.

### 7.2 `ingestion/camera_manager.py`

```python
import json
import logging
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .frame import Frame
from .sources.base import VideoSource
from .sources.file_source import FileSource
from .sources.rtsp_source import RtspSource

log = logging.getLogger("ingestion.manager")


class FpsCounter:
    """Rolling FPS over the last `window` frames."""

    def __init__(self, window: int = 30):
        self._ts = deque(maxlen=window)

    def tick(self) -> None:
        self._ts.append(time.monotonic())

    @property
    def fps(self) -> float:
        if len(self._ts) < 2:
            return 0.0
        span = self._ts[-1] - self._ts[0]
        return (len(self._ts) - 1) / span if span > 0 else 0.0


@dataclass
class CameraConfig:
    camera_id: str
    name: str
    source_type: str          # "file" | "rtsp"
    source: str
    target_fps: Optional[float] = None
    resize_width: Optional[int] = None
    loop: bool = False
    realtime: bool = True
    enabled: bool = True


def load_camera_configs(path: Path) -> List[CameraConfig]:
    with open(path, "r") as f:
        raw = json.load(f)
    configs = []
    for item in raw["cameras"]:
        item = dict(item)
        item["source"] = os.path.expandvars(item["source"])
        configs.append(CameraConfig(**item))
    ids = [c.camera_id for c in configs]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate camera_id in cameras.json")
    return configs


def build_source(cfg: CameraConfig, base_dir: Path) -> VideoSource:
    if cfg.source_type == "file":
        return FileSource(cfg.camera_id, base_dir / cfg.source,
                          target_fps=cfg.target_fps, resize_width=cfg.resize_width,
                          loop=cfg.loop, realtime=cfg.realtime)
    if cfg.source_type == "rtsp":
        return RtspSource(cfg.camera_id, cfg.source,
                          target_fps=cfg.target_fps, resize_width=cfg.resize_width)
    raise ValueError(f"Unknown source_type: {cfg.source_type}")


class CameraWorker(threading.Thread):
    """One thread per camera. Keeps a small bounded queue; when full, the OLDEST
    frame is dropped so latency never grows."""

    def __init__(self, source: VideoSource, queue_size: int = 2):
        super().__init__(daemon=True, name=f"cam-{source.camera_id}")
        self.source = source
        self.frames: "queue.Queue[Frame]" = queue.Queue(maxsize=queue_size)
        self.fps = FpsCounter()
        self.status = "starting"     # starting | running | reconnecting | ended | failed
        self.dropped = 0
        self.total = 0
        self._stop_evt = threading.Event()

    def run(self) -> None:
        if not self.source.open():
            self.status = "failed"
            log.error("[%s] failed to open source", self.source.camera_id)
            return

        while not self._stop_evt.is_set():
            frame = self.source.read()
            if frame is None:
                if self.source.ended:
                    self.status = "ended"
                    break
                self.status = "running" if self.source.connected else "reconnecting"
                time.sleep(0.005)
                continue

            self.status = "running"
            self.total += 1
            self.fps.tick()
            try:
                self.frames.put_nowait(frame)
            except queue.Full:
                try:
                    self.frames.get_nowait()   # drop the oldest
                except queue.Empty:
                    pass
                self.dropped += 1
                self.frames.put_nowait(frame)

        self.source.release()

    def get(self, timeout: float = 0.05) -> Optional[Frame]:
        try:
            return self.frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        self._stop_evt.set()


class CameraManager:
    def __init__(self, sources: List[VideoSource], queue_size: int = 2):
        self.workers: Dict[str, CameraWorker] = {
            s.camera_id: CameraWorker(s, queue_size) for s in sources
        }

    @classmethod
    def from_config(cls, config_path: Path, base_dir: Path) -> "CameraManager":
        configs = [c for c in load_camera_configs(config_path) if c.enabled]
        return cls([build_source(c, base_dir) for c in configs])

    def start_all(self) -> None:
        for w in self.workers.values():
            w.start()

    def stop_all(self) -> None:
        for w in self.workers.values():
            w.stop()
        for w in self.workers.values():
            w.join(timeout=5)

    @property
    def camera_ids(self) -> List[str]:
        return list(self.workers.keys())

    def get_frame(self, camera_id: str, timeout: float = 0.05) -> Optional[Frame]:
        return self.workers[camera_id].get(timeout)

    def stats(self) -> Dict[str, dict]:
        return {
            cid: {
                "status": w.status,
                "fps": round(w.fps.fps, 1),
                "frames": w.total,
                "dropped": w.dropped,
            }
            for cid, w in self.workers.items()
        }
```

### 7.3 Design notes

- **One thread per camera** isolates failures: a stuck RTSP camera cannot block a file camera.
- **Bounded queue with drop-oldest** is the policy for the whole pipeline. When the detector is slower than the cameras, you drop frames instead of letting delay grow. Count drops in `dropped` and surface them later in system health.
- **Per-camera state** (queues, counters, later trackers) is never shared across cameras.
- Threads are fine for I/O-bound decode (OpenCV releases the GIL). Move to processes only if profiling shows a CPU bottleneck.

**Deliverable:** three cameras (two files, one RTSP) producing frames simultaneously.

---

## 8. Task 6: Multi-Camera Viewer Script

`ai-engine/scripts/view_cameras.py` (lives in `ai-engine` because the viewer will become the front end of the detection pipeline tomorrow).

```python
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
```

Run:

```bash
python ai-engine/scripts/view_cameras.py              # window (needs a display)
python ai-engine/scripts/view_cameras.py --headless --seconds 15
```

**WSL note:** `cv2.imshow` needs a display. Newer WSL2 with WSLg works; otherwise use `--headless` and inspect the saved snapshots in `outputs/snapshots/`.

**What you should see:** a grid with camera ID, frame ID, UTC time, FPS (near each camera's `target_fps`), and a `drop` count. A camera with no signal shows a red "NO SIGNAL" tile instead of crashing the viewer.

**Deliverable:** live grid or headless stats for 3 cameras at once.

---

## 9. Task 7: ONVIF Discovery Stub (stretch, keep it small)

ONVIF lets cameras be discovered and queried for their stream URLs. Today you only define the **interface** so the rest of the system can depend on it. Implementation is deferred.

`ingestion/onvif/discovery.py`

```python
from dataclasses import dataclass
from typing import List


@dataclass
class DiscoveredCamera:
    name: str
    host: str
    port: int
    rtsp_url: str


class OnvifDiscovery:
    """Placeholder. A real implementation would use WS-Discovery to find devices
    on the LAN and an ONVIF client (e.g. the `onvif-zeep` package) to read each
    device's stream profile and RTSP URI."""

    def discover(self, timeout: float = 5.0) -> List[DiscoveredCamera]:
        raise NotImplementedError("ONVIF discovery is planned for a later phase")
```

Add one line to `docs/architecture.md` stating that ONVIF discovery is a planned extension and that cameras are configured manually via `cameras.json` for now.

---

## 10. Features Delivered by End of Day 2

- `Frame` model with `camera_id`, `frame_id`, `timestamp`, `video_time_ms`
- `VideoSource` interface with `FileSource` and `RtspSource` implementations
- Frame skipping to a target FPS, aspect-preserving resize, real-time pacing, looping, and graceful end-of-file
- RTSP ingestion with latest-frame reading (no stale buffering) and automatic reconnect with exponential backoff
- Multi-camera `CameraManager` with a thread per camera, bounded drop-oldest queues, and per-camera stats (status, FPS, frames, dropped)
- Config-driven cameras (`cameras.json`) with credential support through environment variables
- Multi-camera viewer with overlays, and a headless mode
- ONVIF interface stub
- Local RTSP simulator workflow for repeatable testing

---

## 11. Tests

`video-ingestion/tests/test_sources.py`. Tests generate their own synthetic video, so they do not depend on your dataset.

```python
import time

import cv2
import numpy as np
import pytest

from ingestion.sources.file_source import FileSource
from ingestion.sources.rtsp_source import RtspSource
from ingestion.camera_manager import CameraManager


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "t.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(90):
        writer.write(np.full((240, 320, 3), (i * 2) % 255, np.uint8))
    writer.release()
    return path


def read_all(src, limit=1000):
    frames = []
    while len(frames) < limit:
        f = src.read()
        if f is None:
            break
        frames.append(f)
    return frames


def test_reads_all_frames_and_metadata(sample_video):
    src = FileSource("T1", sample_video, realtime=False)
    assert src.open()
    frames = read_all(src)
    assert len(frames) >= 89
    assert all(f.camera_id == "T1" for f in frames)
    ids = [f.frame_id for f in frames]
    assert ids == sorted(ids) and ids[0] == 1
    assert src.ended
    src.release()


def test_frame_skipping(sample_video):
    src = FileSource("T1", sample_video, target_fps=10, realtime=False)
    assert src.open()
    frames = read_all(src)
    assert 28 <= len(frames) <= 32       # ~90 frames / 3
    src.release()


def test_resize_keeps_aspect(sample_video):
    src = FileSource("T1", sample_video, resize_width=160, realtime=False)
    assert src.open()
    f = src.read()
    assert f.width == 160 and f.height == 120
    src.release()


def test_loop_does_not_end(sample_video):
    src = FileSource("T1", sample_video, loop=True, realtime=False)
    assert src.open()
    frames = read_all(src, limit=200)
    assert len(frames) == 200 and not src.ended
    src.release()


def test_missing_file_fails_cleanly(tmp_path):
    src = FileSource("T1", tmp_path / "nope.mp4")
    assert src.open() is False


def test_multi_camera_manager(sample_video):
    sources = [FileSource(f"C{i}", sample_video, loop=True, realtime=False)
               for i in range(3)]
    mgr = CameraManager(sources)
    mgr.start_all()
    time.sleep(1.0)
    stats = mgr.stats()
    mgr.stop_all()
    assert set(stats) == {"C0", "C1", "C2"}
    assert all(s["frames"] > 0 for s in stats.values())


def test_rtsp_unreachable_does_not_crash():
    src = RtspSource("R1", "rtsp://127.0.0.1:9/none", reconnect_initial=0.2)
    assert src.open() is True
    time.sleep(1.5)
    assert src.read() is None
    assert src.connected is False
    src.release()
```

Run:

```bash
pytest video-ingestion/tests -v
```

---

## 12. Challenges and How to Handle Them

| Challenge | Why it happens | What to do |
|---|---|---|
| **RTSP lag grows over time** | OpenCV queues frames internally; a slow consumer reads old video | Dedicated reader thread that keeps only the latest frame (done in `RtspSource`); TCP + `nobuffer` options |
| **Stream hangs forever** | `cap.read()` blocks on a half-dead connection | `stimeout` option in `__init__.py`; monitor `last_frame_age` and treat a large value as a stuck stream; daemon threads so shutdown never hangs |
| **Dropouts and flapping connections** | Network issues, camera reboots | Reconnect with exponential backoff (1s → 30s cap), never crash the manager |
| **`stimeout` rejected by FFmpeg** | Option renamed across FFmpeg versions | Try `timeout;5000000`. Test with the simulator and check the log |
| **H.264 / H.265 decode differences** | Codec support depends on the OpenCV/FFmpeg build; H.265 may fail or be CPU-heavy | Check codec with `ffprobe` (Task 1). If a clip will not open, re-encode it to H.264 |
| **Variable frame rate files** | `CAP_PROP_FPS` is wrong, so skipping and pacing drift | Normalize problem clips with `ffmpeg -r` (Task 1.3) |
| **Timestamp confusion** | File time and wall-clock time differ | One convention: `timestamp` = wall-clock UTC at read time, `video_time_ms` kept separately |
| **Frame skipping vs tracking quality** | Low FPS makes objects jump further between frames, which hurts tracking on Day 5 | Keep `target_fps` configurable and record which value you used when you benchmark |
| **CPU load with several streams** | Decode plus resize per stream | Downscale early (`resize_width`), skip frames with `grab()`, and measure CPU per camera. Move to processes only if you must |
| **Display not available (WSL / servers)** | `cv2.imshow` needs a GUI | Headless mode with saved snapshots |
| **Frame timing jitter in `realtime` pacing** | `sleep` is not exact | Deadline-based pacing (done), not fixed `sleep(1/fps)` |
| **Threads not shutting down** | Blocking calls | Daemon threads, stop events, join with timeouts |
| **Credentials leaking into Git** | RTSP URLs include username and password | `${ENV_VAR}` in `cameras.json`, real values only in `.env` (gitignored) |
| **Docker port issues for MediaMTX** | Port 8554 in use or blocked | Change the published port and update the URL |

### Do NOT do today

- Object detection or any model inference (Day 3)
- Tracking, zones, lines, or events (Days 5-6)
- Writing annotated videos (Day 7)
- Redis or database writes of frames or events
- ONVIF implementation beyond the stub
- Frame encoding or streaming to the dashboard

---

## 13. Verification Checklist (Definition of Done)

- [ ] 3-5 test clips in `datasets/videos/`, with metadata and sources recorded in `datasets/README.md`
- [ ] `pip install -e video-ingestion` works; `import ingestion` succeeds
- [ ] `docs/decisions/0002-timestamp-convention.md` exists
- [ ] `pytest video-ingestion/tests -v` passes
- [ ] Viewer shows **3 cameras at once** (2 files + 1 RTSP) with camera ID, frame ID, time, and FPS overlays
- [ ] Displayed FPS is close to each camera's `target_fps`
- [ ] Looping works: a short clip keeps playing without the camera ending
- [ ] A non-looping file ends cleanly (`status = ended`) without crashing the other cameras
- [ ] **Dropout test:** stop and restart the `ffmpeg` RTSP push. CAM_003 shows `reconnecting`, then recovers by itself
- [ ] **Not-started test:** start the app before the RTSP stream exists. It starts, retries, and connects when the stream appears
- [ ] RTSP latency is small and does not grow during a 5 minute run
- [ ] A bad file path or unreachable URL only affects that camera; others keep running
- [ ] No credentials or videos staged in Git (`git status` check)

---

## 14. Commits

```bash
git checkout feature/detection
git add .
git status        # confirm no videos, .env, or weights are staged
```

Suggested commits:

1. `feat(ingestion): add Frame model and VideoSource interface`
2. `feat(ingestion): add FileSource with frame skipping, resize, pacing, and loop`
3. `feat(ingestion): add RtspSource with latest-frame reader and reconnect`
4. `feat(ingestion): add CameraManager with per-camera workers and config loading`
5. `feat: add multi-camera viewer script`
6. `test(ingestion): add source and manager tests`
7. `docs: add timestamp convention, dataset metadata, and ONVIF note`

At end of day:

```bash
git checkout develop
git merge feature/detection
git push origin develop feature/detection
```

---

## 15. Preparing for Day 3

Day 3 starts YOLO inference on the frames you produce today.

1. **Pick one good frame per clip** (or save snapshots from the viewer) to use as quick single-image detection tests.
2. **Check your hardware:** run `nvidia-smi` and `python -c "import torch; print(torch.cuda.is_available())"` and write the result in `docs/benchmarks.md`. Your Day 4 benchmark table depends on it.
3. **Check that the model loads:** `python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"` and that the weights file sits in `ai-engine/models/`.
4. **Decide your starting model:** `yolov8n` (fastest) or `yolov8s` (more accurate). Day 3 will compare them.
5. **Note which clips look hardest** (night, crowded, small distant objects). You will use them to study failure cases.
6. **Write down any problems from today** in `docs/decisions/` so they are not forgotten.

**Day 3 goal:** load a pretrained YOLO model, run inference on a single frame and then a video, filter to person and vehicle classes, set confidence and NMS thresholds, and draw boxes with labels and confidence, consuming `Frame` objects from today's `CameraManager`.
