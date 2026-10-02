# AI Engine (`ai-engine`)

The **AI Engine** is the core computer vision and intelligence processing subsystem of the Border AI platform. It ingests frames emitted by `video-ingestion`, performs real-time object detection and multi-object tracking, calculates spatial zone and tripwire intrusions, evaluates behavioral rules, and generates structured security observations and risk scores.

---

## 1. Directory Structure

```text
ai-engine/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI REST application entrypoint (:8000)
│   ├── config.py              # Environment variable (.env) and YAML config loader
│   ├── api/                   # REST API routes and endpoints
│   ├── detection/             # Object detection wrappers (YOLOv8)
│   ├── tracking/              # Multi-object tracking algorithms (ByteTrack / BoT-SORT)
│   ├── analytics/             # Spatial geometry (polygons, lines, loitering)
│   ├── pipeline/              # Frame processing coordinator & visualizer
│   ├── schemas/               # Pydantic data schemas (Detection, Track, Event)
│   ├── utils/                 # Geometry algorithms, timing, and logging
│   ├── anpr/                  # Automatic Number Plate Recognition (Week 2)
│   ├── identity/              # Face detection and Re-ID modules (Week 2)
│   └── rules/                 # Threat scoring engine (Week 2)
├── models/                    # Pretrained weights (e.g., yolov8n.pt - gitignored)
├── scripts/
│   └── view_cameras.py        # Multi-camera live grid viewer with telemetry
├── tests/                     # Unit and integration tests for AI models
├── Dockerfile                 # Container specification for GPU/CPU inference
└── requirements.txt           # Python dependencies (PyTorch, Ultralytics, OpenCV, FastAPI)
```

---

## 2. Core Technologies

- **Python 3.11**: Runtime environment.
- **Ultralytics YOLOv8**: Primary object detection network (`person`, `car`, `truck`, `bus`, `motorcycle`, `bicycle`).
- **ByteTrack / BoT-SORT**: Multi-object tracking maintaining persistent track IDs and motion trajectories.
- **FastAPI & Uvicorn**: Asynchronous web framework exposing model endpoints, stream control, and health status.
- **OpenCV & NumPy**: Matrix manipulation, bounding box rendering, and image preprocessing.
- **Shapely**: High-speed computational geometry for polygon point-in-polygon containment and line intersections.

---

## 3. How to Use & Run

### Prerequisites
Activate the root virtual environment:
```bash
source ../.venv/bin/activate   # or from repo root: source .venv/bin/activate
```

### Run the FastAPI Service
Start the service with automatic reload on port 8000:
```bash
cd ai-engine
uvicorn app.main:app --reload --port 8000
```
Or from the project root:
```bash
make ai
```

### Health Check & Interactive API Docs
- **Health check**: `curl http://localhost:8000/health`
  ```json
  {"service": "ai-engine", "status": "ok", "env": "development", "cuda": false, "device": "cpu"}
  ```
- **Swagger Documentation**: Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

### Run Multi-Camera Live Viewer
Display all active camera streams with telemetry overlay:
```bash
# GUI Display mode
python ai-engine/scripts/view_cameras.py

# Headless mode with automated snapshot saving
python ai-engine/scripts/view_cameras.py --headless --seconds 15
```

---

## 4. Architectural Guidelines
- **Models produce *observations*, not threat scores**: Detections and tracks are raw observations. Business logic, spatial rules, and risk scoring are decoupled into the rule engine.
- **Normalized coordinates**: All bounding boxes and polygon queries are processed in normalized `[0.0, 1.0]` space to remain resolution-independent.
