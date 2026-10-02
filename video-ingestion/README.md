# Video Ingestion Subsystem (`video-ingestion`)

The **Video Ingestion** module is an installable Python package (`ingestion`) responsible for reliable, low-latency video capture from local pre-recorded video files and live network RTSP / ONVIF IP-camera streams.

---

## 1. Directory Structure

```text
video-ingestion/
├── ingestion/
│   ├── __init__.py            # Low-latency FFmpeg TCP environment flags
│   ├── frame.py               # Standard Frame dataclass
│   ├── camera_manager.py      # Multi-camera thread manager & drop-oldest queues
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py            # VideoSource ABC and resize_keep_aspect helper
│   │   ├── file_source.py     # FileSource (frame skipping, resize, pacing, loop)
│   │   └── rtsp_source.py     # RtspSource (latest-frame thread & reconnect backoff)
│   └── onvif/
│       ├── __init__.py
│       └── discovery.py       # ONVIF WS-Discovery interface stub
├── tests/
│   └── test_sources.py        # Automated test suite (7 tests)
├── pyproject.toml             # Setuptools build specification for editable install
├── Dockerfile                 # Standalone container build definition
└── requirements.txt           # opencv-python, numpy, python-dotenv, pyyaml
```

---

## 2. Core Concepts & Design Principles

### 1. Unified `Frame` Dataclass
Every frame emitted by any source adheres to a standardized format:
- `camera_id`: Unique identifier (e.g., `CAM_001`).
- `frame_id`: Monotonically increasing integer per camera.
- `timestamp`: UTC wall-clock epoch seconds (`time.time()`) at capture time (ADR 0002).
- `video_time_ms`: Position within a video container (0.0 for live streams).
- `image`: Decoded BGR NumPy array `(H, W, 3)`.
- `source_fps`: Native frame rate reported by the camera hardware.

### 2. Zero-Stale-Buffer RTSP Reader
Standard OpenCV `VideoCapture` internally buffers incoming network packets, leading to growing video lag if consumption is delayed. `RtspSource` solves this by running a dedicated background reader thread that decodes continuously and retains **only the single newest frame**.

### 3. Fault-Tolerant Reconnect
If a camera feed drops or network connectivity is interrupted, `RtspSource` does not crash the application. It automatically retries with exponential backoff (1s → 2s → 4s ... up to 30s) and seamlessly resumes frame streaming once the feed returns.

### 4. Drop-Oldest Bounded Queuing
`CameraManager` allocates one isolated worker thread per camera feed. Output frames are placed in a small bounded queue (`maxsize=2`). If downstream AI inference is slower than the incoming frame-rate, the **oldest frame is dropped**, ensuring downstream detectors always consume real-time imagery.

---

## 3. How to Use & Test

### Installation (Editable Mode)
```bash
source .venv/bin/activate
pip install -e video-ingestion
```

### Run Automated Unit & Integration Tests
```bash
pytest video-ingestion/tests -v
```

### Python API Example
```python
from pathlib import Path
from ingestion.camera_manager import CameraManager

base_dir = Path(".")
mgr = CameraManager.from_config(base_dir / "configs" / "cameras.json", base_dir)
mgr.start_all()

# Fetch latest frame for a camera
frame = mgr.get_frame("CAM_001", timeout=0.05)
if frame is not None:
    print(f"Captured {frame.camera_id} frame #{frame.frame_id} at {frame.width}x{frame.height}")

# Inspect runtime performance stats
print(mgr.stats())

mgr.stop_all()
```
