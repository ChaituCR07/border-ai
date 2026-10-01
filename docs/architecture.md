# Border AI Architecture

## 1. Overview
The **AI-Based Intelligent Video Analytics Platform for Border Surveillance (`border-ai`)** converts existing CCTV and IP-camera infrastructure into an automated, real-time surveillance analytics system. It ingests video feeds, applies high-performance object detection and multi-object tracking, performs identity and license plate recognition (ANPR), monitors spatial boundaries/virtual lines, evaluates behavioural rules, computes dynamic threat scores, correlates events across multiple camera angles, and dispatches prioritized real-time alerts to command and investigation dashboards.

## 2. Core Processing Pipeline

```text
CCTV / RTSP / ONVIF
        ↓
Video Ingestion
        ↓
Object Detection (YOLO)
        ↓
Multi-Object Tracking (ByteTrack)
        ↓
ANPR / Identity Intelligence
        ↓
Watchlist Verification
        ↓
Zone & Behaviour Analysis
        ↓
Threat Scoring
        ↓
Cross-Camera Correlation
        ↓
Prioritized Alert
        ↓
Command Dashboard → Investigation Dashboard
```

## 3. Component Architecture

| Component | Tech | Port | Responsibility |
|---|---|---|---|
| **ai-engine** | Python, FastAPI, YOLO, ByteTrack | 8000 | Detection, tracking, zone analytics, event extraction |
| **video-ingestion** | Python, OpenCV, FFmpeg | Library | Camera/file/RTSP stream capture and frame scheduling |
| **backend** | Node.js, TypeScript, Express | 4000 | Core API, data persistence, event streams, WebSockets |
| **frontend** | React, TypeScript, Vite | 5173 | Tactical command dashboard and investigation interface |
| **PostgreSQL** | postgres:16 | 5432 | Relational storage for cameras, watchlists, events, and snapshots |
| **Redis** | redis:7 | 6379 | Redis Streams high-throughput event bus & pub/sub |

## 4. Fundamental Design Principle
> **AI models produce *observations*; the rule engine turns observations into *events*; the scoring engine turns events into a *risk score*. Models never decide "threat" directly.**

This separation guarantees transparency, explainability, deterministic alert policies, and zero uncontrolled black-box hallucination in security-critical border domains.

## 5. Planned Data Flow
```text
[Camera/RTSP/File] 
       ↓ 
[video-ingestion]
       ↓ 
[ai-engine] (Detection -> Tracking -> Zones -> Scoring)
       ↓ (Redis Streams)
[backend] (Persists to PostgreSQL, broadcasts to WebSocket clients)
       ↓ (WebSocket / REST)
[frontend] (Command Dashboard real-time live alert view)
```

## 6. Repository Layout
```text
border-ai/
├── ai-engine/              # Python: detection, tracking, zone analysis, FastAPI
├── video-ingestion/        # Python: stream capture, RTSP, OpenCV sources
├── backend/                # Node.js + TypeScript Express backend
├── frontend/               # React + TypeScript Vite dashboard
├── database/               # SQL schemas, migrations, seeds
├── configs/                # cameras.json, zones/, app.yaml, rules.json
├── datasets/               # Local test video clips (gitignored)
├── outputs/                # Annotated videos, snapshots, logs (gitignored)
├── docker/                 # Container configs, postgres init scripts
├── docs/                   # Architecture, benchmarks, ADR decision log
└── scripts/                # Setup and automation scripts
```

## 7. Local Development Approach
- **Infrastructure (PostgreSQL + Redis)**: Runs in lightweight, healthchecked Docker containers.
- **Application Services (AI Engine, Backend, Frontend)**: Run directly on the host during initial development (Weeks 1-2) to avoid GPU containerization overhead, enabling rapid debugging and iteration. Complete multi-container Docker Compose is finalized in Weeks 3-4.

## 8. Configuration Approach
- `.env`: Secrets, database passwords, network endpoints (gitignored, `.env.example` committed).
- `configs/`: Declarative JSON/YAML defining camera sources, polygon coordinates, and detection thresholds.

## 9. Privacy and Ethical Policy
All video analytics testing must be conducted solely using authorized, synthetic, or publicly licensed surveillance datasets (COCO, MOT17, UFPR-ALPR). No unauthorized personal data is retained or processed.
