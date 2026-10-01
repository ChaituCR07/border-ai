# AI-Based Intelligent Video Analytics Platform for Border Surveillance (`border-ai`)

> Transforming existing CCTV and IP-camera infrastructure into an autonomous, real-time tactical surveillance intelligence platform using edge computer vision, multi-object tracking, ANPR, spatial behavioral analytics, and deterministic threat scoring.

---

## 1. Problem Statement

Modern border security checkpoints and perimeter surveillance operations rely on extensive networks of legacy CCTV and IP cameras. However, this infrastructure faces severe operational limitations:

- **Cognitive Fatigue & Human Limitations:** Security personnel monitoring dozens of video monitors simultaneously experience rapid cognitive exhaustion, resulting in missed breaches, unauthorized crossings, and slow incident recognition.
- **Passive vs. Active Security:** Traditional CCTV is forensic (recording footage for investigation after an intrusion occurs) rather than proactive (detecting and alarming while an intrusion is underway).
- **Cross-Camera Blindspots:** Disconnected camera feeds fail to track subjects or vehicles across physical transition zones, requiring tedious manual timeline reconstruction.
- **Information Overload & False Alarms:** Environmental factors (wildlife, swaying vegetation, shadows, weather changes) trigger excessive false alarms in naive motion sensors, leading operators to ignore alerts.
- **Hardware Replacement Costs:** Replacing existing camera deployments with specialized AI-embedded cameras requires prohibitive capital expenditure.

### The Opportunity
By adding a software-defined AI analytics layer on top of **existing ONVIF and RTSP video feeds**, security teams can upgrade passive camera networks into an intelligent, active surveillance mesh without replacing physical camera hardware.

---

## 2. Project Overview & Solution

**Border AI** is an end-to-end, event-driven intelligent video surveillance platform designed for perimeter defense, checkpoint monitoring, and border management.

It ingests raw RTSP streams or video files, detects and classifies persons and vehicles in real time, maintains persistent identities across frames via multi-object tracking, verifies license plates against alert watchlists, monitors restricted spatial polygons and virtual boundary tripwires, computes dynamic threat scores (0–100), and streams prioritized alerts to real-time command dashboards.

### Core Processing Pipeline

```text
       Existing CCTV / RTSP / ONVIF Cameras
                        │
                        ▼
       [1] High-Throughput Video Ingestion (OpenCV / FFmpeg)
                        │
                        ▼
       [2] Real-Time Object Detection (YOLOv8)
                        │
                        ▼
       [3] Multi-Object Tracking (ByteTrack / BoT-SORT)
                        │
                        ▼
       [4] License Plate Recognition (ANPR / OCR)
                        │
                        ▼
       [5] Spatial & Behavioral Analytics (Polygons / Virtual Lines / Loitering)
                        │
                        ▼
       [6] Explainable Threat Scoring Engine (0 - 100 Scale)
                        │
                        ▼
       [7] High-Speed Event Bus (Redis Streams)
                        │
                        ▼
       [8] Persistence & Cross-Camera Correlation (PostgreSQL 16)
                        │
                        ▼
       [9] Real-Time Tactical Dashboard (React + WebSockets)
```

---

## 3. Technology Stack

The platform is built using a modern, scalable, microservice-ready architecture combining high-performance Python computer vision with an asynchronous TypeScript backend and a reactive operator frontend.

### AI Engine & Computer Vision
- **Python 3.11**: Core runtime for AI processing and model execution.
- **Ultralytics YOLOv8**: Real-time object detection and classification (`person`, `vehicle`, `bicycle`, `bus`, `truck`).
- **ByteTrack / BoT-SORT**: Low-latency multi-object tracking with persistent track IDs and occlusion handling.
- **PaddleOCR / Fast-ANPR**: Character segmentation and text recognition for vehicle license plates.
- **OpenCV & NumPy**: Hardware-accelerated frame manipulation, drawing overlays, and color-space conversions.
- **Shapely**: High-speed computational geometry for polygon point-in-polygon checks and line-crossing intersection algorithms.
- **FastAPI & Uvicorn**: High-performance asynchronous REST API exposing AI inference status and stream control.

### Video Ingestion & Streaming
- **FFmpeg & OpenCV VideoCapture**: Efficient decoding of RTSP, ONVIF, and local video container formats.
- **Threaded Frame Queuing**: Decoupled frame grabbers preventing stream lag and socket buffer bloat.

### Event Bus & Messaging
- **Redis 7 (Redis Streams & Pub/Sub)**: Decouples high-frequency CV detections from relational database persistence and powers real-time message broadcasting.

### Backend & Data Persistence
- **Node.js 20+ & TypeScript**: Type-safe, asynchronous event consumer and business logic service.
- **Express.js**: REST API gateway for cameras, watchlists, rules, and incident reports.
- **PostgreSQL 16**: Relational storage for camera metadata, zone definitions, watchlists, security incidents, and audit logs.
- **WebSockets (`ws`)**: Sub-second bi-directional event pushing from backend to frontend operator consoles.

### Command & Investigation Dashboard
- **React 18 / 19 & TypeScript**: Interactive user interface for tactical security operations.
- **Vite**: Ultra-fast build tooling and hot-module replacement.
- **Modern Responsive CSS**: Clean, high-contrast, dark-mode-optimized tactical interface.

### Infrastructure & Tooling
- **Docker & Docker Compose**: Containerized database (PostgreSQL 16) and message broker (Redis 7) with integrated healthchecks.
- **Git & GitHub**: Version-controlled branching workflow (`main`, `develop`, `feature/*`).

---

## 4. Fundamental Design Principles

1. **Observations vs. Events vs. Threats:**
   - **AI models produce *observations*** (e.g., "Person detected at coordinate (x,y) with confidence 0.88").
   - **Rule engines produce *events*** (e.g., "Person crossed into Restricted Polygon Zone B at 02:14 AM").
   - **Scoring engines calculate *threat scores*** (e.g., "Restricted zone + Night hours + Loitering = Threat Score 85/100").
   - *AI models never directly trigger security alerts.* This ensures complete auditability and zero black-box hallucination.
2. **Normalized Spatial Coordinates:**
   - All spatial boundaries (zones, tripwires) are defined as normalized coordinates `(0.0 - 1.0)`. They automatically adapt to any camera resolution (720p, 1080p, 4K) without manual recalibration.
3. **Decoupled Asynchronous Processing:**
   - Heavy video inference does not block API requests; Redis Streams act as a buffer between detection frame-rates and database write limits.

---

## 5. Threat Scoring Framework

The threat engine dynamically evaluates contextual factors to compute a composite threat score between **0 and 100**:

| Factor | Weight / Additive Points | Rationale |
|---|---|---|
| **Restricted Zone Incursion** | +35 pts | Subject physically inside a restricted security boundary |
| **Virtual Line Breach (IN direction)** | +25 pts | Inward perimeter crossing |
| **Night Hours Detection (22:00 - 05:00)** | +20 pts | High-risk temporal window |
| **Watchlist Plate Match** | +40 pts | Vehicle flagged on stolen or surveillance watchlists |
| **Persistent Loitering (> 30s)** | +15 pts | Stationary subject exhibiting suspicious dwelling |
| **Speed Anomaly / Running** | +15 pts | Rapid acceleration away from checkpoint boundary |

- **Threat Score < 40:** Informational / Low priority
- **Threat Score 40 – 69:** Warning / Medium priority (notifies operator)
- **Threat Score ≥ 70:** Critical Alarm / High priority (triggers visual sirens, snapshot dispatch, and prioritized alert log)

---

## 6. Repository Layout

```text
border-ai/
│
├── ai-engine/                     # Computer vision inference & analytics
│   ├── app/
│   │   ├── main.py                # FastAPI entry point (:8000)
│   │   ├── config.py              # Environment & YAML loader
│   │   ├── detection/             # YOLO detector wrapper
│   │   ├── tracking/              # ByteTrack multi-object tracker
│   │   ├── analytics/             # Polygons, tripwires, loitering
│   │   ├── pipeline/              # Frame processing coordinator
│   │   ├── anpr/                  # License plate OCR (Week 2)
│   │   └── rules/                 # Threat scoring engine (Week 2)
│   ├── models/                    # Pretrained weights (yolov8n.pt)
│   └── requirements.txt
│
├── video-ingestion/               # Stream ingestion & camera management
│   ├── ingestion/
│   │   ├── sources/               # FileSource & RTSPSource
│   │   ├── camera_manager.py      # Multi-camera stream scheduler
│   │   └── frame.py               # Frame dataclass
│   └── requirements.txt
│
├── backend/                       # Node.js + TypeScript service
│   ├── src/
│   │   ├── index.ts               # Express server (:4000)
│   │   ├── db/                    # PostgreSQL connection & queries
│   │   ├── streams/               # Redis Streams consumer
│   │   └── websocket/             # Real-time alert broadcaster
│   └── package.json
│
├── frontend/                      # React + TypeScript operator dashboard
│   ├── src/
│   │   ├── App.tsx                # Tactical console & health monitor
│   │   ├── components/            # Camera feeds, alert panels, timelines
│   │   └── services/              # API & WebSocket client
│   └── package.json
│
├── configs/                       # Declarative behaviors & configurations
│   ├── app.yaml                   # Model, confidence, & tracker parameters
│   ├── cameras.json               # Camera feeds, RTSP URLs, target FPS
│   └── zones/                     # Per-camera normalized boundary polygons
│
├── docker/                        # Containerization & database setup
│   ├── postgres/init.sql          # DB bootstrap script
│   └── docker-compose.yml         # PostgreSQL 16 & Redis 7 services
│
├── docs/                          # Architecture specs, benchmarks & ADRs
│   ├── architecture.md            # Detailed system architecture
│   ├── benchmarks.md              # Performance metrics tracking
│   └── decisions/                 # Architecture Decision Records (ADRs)
│
├── Makefile                       # Development shortcuts
└── README.md                      # Project documentation
```

---

## 7. Quick Start & Local Setup

### Prerequisites
- **Git**
- **Docker Desktop** (or Docker Engine)
- **Python 3.10+** (3.11 recommended)
- **Node.js 20 LTS+** & **npm**

### Step-by-Step Installation

#### 1. Clone the Repository & Configure Environment
```bash
git clone https://github.com/ChaituCR07/border-ai.git
cd border-ai
cp .env.example .env
```

#### 2. Start PostgreSQL & Redis Infrastructure
```bash
docker compose up -d
docker compose ps
```
*Both `borderai-postgres` and `borderai-redis` will show `(healthy)`.*

#### 3. Setup Python Virtual Environment & AI Engine
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r ai-engine/requirements.txt -r video-ingestion/requirements.txt
```

#### 4. Run the AI Engine
```bash
cd ai-engine
uvicorn app.main:app --reload --port 8000
```
*Health endpoint: `curl http://localhost:8000/health`*  
*Swagger Documentation: `http://localhost:8000/docs`*

#### 5. Run the Backend API
In a new terminal:
```bash
cd backend
npm install
npm run dev
```
*Health endpoint: `curl http://localhost:4000/health`*

#### 6. Run the Frontend Dashboard
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
*Dashboard accessible at: `http://localhost:5173`*

---

## 8. Convenience Shortcuts (Makefile)

```bash
make up         # Start PostgreSQL and Redis Docker containers
make down       # Stop Docker containers
make ai         # Start FastAPI AI Engine on port 8000
make backend    # Start Node.js Express backend on port 4000
make frontend   # Start Vite React frontend on port 5173
```

---

## 9. Ethics, Privacy & Compliance

This platform is developed strictly for research, portfolio demonstration, and defensive perimeter surveillance.
- **Dataset Policy:** Testing utilizes publicly available, open-access benchmark datasets (COCO, MOT17, UFPR-ALPR) and synthetic simulation clips.
- **Zero Surveillance of Private Spaces:** Coordinate boundaries are calibrated exclusively to public/restricted perimeter perimeters.
- **Retention & Compliance:** All snapshot and telemetry retention follows organization-level data governance and local legal guidelines.

---

## 10. License
This project is licensed under the [MIT License](LICENSE).
