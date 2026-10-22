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

## 10. ONVIF Stream Discovery Note
Automatic ONVIF camera discovery across the local subnet is currently modeled as an architectural interface stub (`ingestion/onvif/discovery.py`). Real-world IP-camera streams and credentials are configured explicitly via `configs/cameras.json` and `.env`.

---

## 11. Multi-Object Tracking Architecture (`ai-engine`)

The tracking subsystem decouples model detection from temporal tracking:
1. **`Detector` Output (`FrameDetections`):** Raw single-frame bounding boxes proposals.
2. **`CameraTracker` (ByteTrack):** Per-camera tracker applying two-stage association (high-confidence detections first, low-confidence boxes second for occlusion rescue).
3. **`TrackStore`:** Maintains stateful track lifecycle (`ACTIVE` → `LOST` → `REMOVED`), computes confidence-weighted majority vote for classification stability, records ground-contact point trajectories (`trail`), and produces lifecycle updates (`TrackUpdate`) consumed by downstream zone and alert engines.
4. **`MultiCameraTracker`:** Aggregator managing concurrent, independent trackers keyed strictly by `(camera_id, track_id)`.

---

## 12. Spatial Rules & Event Analytics Architecture (`ai-engine`)

The analytics subsystem evaluates spatio-temporal trajectories against declarative policies:
1. **`RuleEngine` Facade:** Loads and caches camera-specific configurations (`configs/zones/<camera_id>.json`).
2. **`ZoneEngine`:** Applies point-in-polygon tests to bottom-center anchor points with hysteresis state machines, tracking occupancy, dwell duration, and localized loitering spans.
3. **`LineEngine`:** Evaluates movement vectors across finite line segments with normal-oriented direction classification (`IN` / `OUT`), dead-band hovering suppression, and per-track cooldowns.
4. **Event Generation:** Produces normalized `Event` records published to disk and Redis Streams without coupling to alert rendering.

---

## 13. Automatic Number Plate Recognition (ANPR) Architecture (`ai-engine`)

Day 8 integrates automatic license plate recognition into the analytics pipeline using an asynchronous worker pattern:

```text
Inference Thread                                   ANPR Background Worker Thread
────────────────                                   ─────────────────────────────
Frame Tracks (ByteTrack)
      │
      ├─ Filter: Class in [car, truck, bus, ...]
      ├─ Filter: Bounding box >= 90px width
      ├─ Filter: Not touching frame boundary
      ├─ Schedule: Every 5 frames until stable
      │
      ▼
Submit Job (Deep-copy vehicle crop)
      │
      ▼ [Bounded Queue (Size 32)]
      │ (Offline: block / Live: drop-oldest) ────► Pull Job
                                                    │
                                                    ▼
                                            Plate Locator
                                            (YOLO or Lower-Region Fallback)
                                                    │
                                                    ▼
                                            Quality Gate
                                            (Sharpness >= 40, Width >= 50px)
                                                    │
                                                    ▼
                                            Image Preprocessing
                                            (CLAHE + Resizing + Replicate Border)
                                                    │
                                                    ▼
                                            PaddleOCR Engine (PP-OCRv6)
                                                    │
                                                    ▼
                                            Plate Format & Positional Rules
                                            (Indian Layouts / Generic Fallback)
                                                    │
                                                    ▼
                                            Consensus Engine
                                            (Exact-string & Character-level voting)
                                                    │
                                                    ├─ First Stable? ──► Emit PLATE_RECOGNIZED (final: false)
                                                    │
                                                    └─ Vehicle Ended? ─► Emit Final Event & Write plates.jsonl
```

### Key Architectural Traits:
1. **Decoupled Worker:** Heavy text detection and character recognition (~270-320 ms) run entirely on a separate thread (`anpr-worker`). The inference thread never waits on OCR.
2. **Dynamic Early Stopping:** Once a plate achieves stability via multi-frame consensus (`min_reads: 3`, `stable_share: 0.6`), OCR scheduling stops immediately for that vehicle track.
3. **Dual Voting:** Combines weighted string-level voting with positional character-level voting across the dominant length to repair intermittent misreads.
4. **Data Privacy Isolation:** License plate crops are stored locally in `outputs/runs/<id>/anpr/plates/` and strictly gitignored.

---

## 8. Watchlist Processing Stage

```
   ANPR Worker Thread                   Watchlist Background Worker
  ──────────────────────               ──────────────────────────────
   PLATE_RECOGNIZED Event ─────────────► Bounded Lookup Queue (size 100)
                                                    │
                                                    ▼
                                            De-duplicate Track
                                            (1 lookup per distinct plate)
                                                    │
                                                    ▼
                                            PostgreSQL Lookup
                                            (Exact match via partial index)
                                            (Same-length candidates for near)
                                                    │
                                          [Fail? In-memory Snapshot]
                                                    │
                                                    ▼
                                            Score & Status Decision
                                            (Alert >= 0.70 conf; Near = Review)
                                                    │
                                                    ▼
                                            Camera Cooldown Gate
                                            (Suppress repeat alerts within 60s)
                                                    │
                                                    ├─ Emits WATCHLIST_MATCH Event
                                                    ├─ Records Hit in watchlist_hits
                                                    └─ Updates Active Track Flags (Red Box overlay)
```

### Architectural Guarantees:
1. **Zero Vision Pipeline Blocking:** Background worker isolation guarantees that database timeouts or network stalls never affect camera ingestion, tracking, or rule evaluation.
2. **Deterministic Offline Execution:** Cooldown calculations rely strictly on stream frame timestamps rather than system wall clock.
3. **Transparent Outage Survivability:** Lookups continue uninterrupted via memory snapshot when the database is temporarily offline, buffering hits until reconnection.

---

## 9. Identity & Person Re-ID Processing Stage

```
   Inference Thread                        Identity Worker Thread
  ──────────────────                      ────────────────────────
   Person Tracks (BBoxes) ───────────────► Bounded Queue (size 64)
   (Crops copied before rendering)                   │
                                                     ▼
                                        Face Detection (Upper crop)
                                        Quality Gate (Score, Size, Yaw, Blur)
                                        Face Embedding (SFace / ArcFace)
                                        Track Aggregator (Weighted Mean)
                                        Consistency Check (>= 0.75)
                                                     │
                                                     ├─ Face Match? ──► WATCHLIST_MATCH (review)
                                                     │                  Hit Stored (match_basis: face)
                                                     │                  Flag: "HIGH REVIEW FACE"
                                                     │
                                        Appearance Embedding (ColorLayout / ONNX)
                                        ReidGallery Search (Recent tracks across cameras)
                                                     │
                                                     └─ Re-ID Match? ─► REID_MATCH (candidate)
                                                                        Label: "= CAM_001 #12?"
```

### Architectural Traits:
1. **Zero-Latency Impact on Ingestion:** Face detection and appearance feature extraction run asynchronously. In live mode, oldest jobs are dropped when the queue fills.
2. **Crop Isolation:** Person crops are copied immediately upon submission, preventing frame visualizer race conditions.
3. **No Biometric Persistence:** Re-ID gallery entries expire automatically in memory after 900 seconds. No face or person images are ever stored on disk.

## 10. Behaviour Engine (Deterministic Rules)

```
   Inference Thread                        Worker Threads (ANPR / Watchlist / ID)
  ──────────────────                      ────────────────────────────────────────
   Zones & Lines Observations ──┐                 Observations (Plate / Match)
                                │                              │
                                ▼                              ▼
                    ┌──────────────────────────────────────────────┐
                    │      TrackContext & BehaviourEngine         │
                    │  (Synchronous evaluation per frame)          │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                                 Behaviour Events (JSONL)
                            (ZONE_VIOLATION, DIRECTION_VIOLATION,
                             LOITERING_VIOLATION, AFTER_HOURS, ...)
                                           │
                                           ▼
                                 [Threat Scoring Stage] (Day 12)
```

### Architectural Traits:
1. **Separation of Observations and Decisions:** Vision models produce observations (detections, tracks, plate reads, watchlist hits); the behaviour engine turns observations into events. No vision model decides alert levels directly.
2. **Deterministic Time:** Offline evaluation supports simulated clocks (`--clock-start`), ensuring temporal rule reproducibility independent of execution wall time.
3. **Episode-Based Suppression:** Alerts fire once per episode with configurable `rearm_s` and `cooldown_s`, preventing frame-by-frame alert flooding.

## 11. Threat Scoring Engine

```
   Observations & Behaviour Events
                 │
                 ▼
       ┌──────────────────┐
       │   ThreatScorer   │
       │   (app/threat/)  │
       └─────────┬────────┘
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
 Live Frame Visualizer    THREAT_ALERT (JSONL)
 (T60 HIGH, Bounding Box  (Escalation only,
  Color: Yellow/Orange/Red) Snapshot on Disk)
                            │
                            ▼
                  [Redis Stream] (Day 13)
```

### Architectural Traits:
1. **Entity-Based Aggregation:** Threat state is tracked on the logical entity rather than individual bounding boxes or events. License plate readings merge fragmented tracks of the same vehicle.
2. **Decaying Relevance:** Contributions expire outside a 10-minute sliding window (`window_s: 600`), ensuring past infractions do not create perpetual high-threat entities.
3. **Escalation-Only Alerting:** Prevents alert fatigue by raising `THREAT_ALERT` only upon initial threshold crossing or level increases (`LOW` -> `MEDIUM` -> `HIGH` -> `CRITICAL`).
4. **Evidence Snapshots:** Clean, pre-annotation video frames are captured when alerts fire and saved to `outputs/runs/<run_id>/snapshots/` for visual verification.

## 12. Redis Event Pipeline & Processor

```
     Vision Pipeline (Edge Camera Node)
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 Local Journal (Disk)       In-Memory Buffers
 (events.jsonl - Source     (_high: 5k, _low: 20k)
  of Truth)                         │
                                    ▼
                         EventPublisher Thread
                         (Non-blocking, retry backoff)
                                    │
                                    ▼
                         Redis Streams Broker
                         (surveillance.events,
                          surveillance.alerts)
                                    │
                                    ▼
                          EventProcessor Service
                          (Consumer group: 'processor')
                          ┌─────────┴─────────┐
                          ▼                   ▼
                  Idempotency Filter   Dead-Letter Queue
                  (dedupe_cache: 20k) (surveillance.events.dead)
                          │
                          ▼
                  Pluggable Sinks
                  ├── ConsoleAlertSink
                  ├── JsonlFileSink
                  └── PostgresEventSink (Day 14)
```

### Architectural Traits:
1. **Zero-Latency Ingress:** Vision inference threads perform an in-memory queue push that returns in microseconds. Network I/O and Redis round-trips run on a dedicated publisher thread.
2. **Dual-Layer Persistence:** The local camera node journal (`events.jsonl`) is written synchronously first; the Redis Stream is a decoupled, retryable transmission copy. If Redis is down, missed events are recovered via journal replay.
3. **Priority Overflow Shedding:** Under sustained broker outages, noisy observations (`ZONE_ENTER`, `LINE_CROSSING`) are shed first when buffers reach capacity, protecting high-priority `THREAT_ALERT` messages.
4. **Resilient Consumer Groups:** Unacknowledged messages resulting from consumer worker crashes are automatically reclaimed by sibling workers via `XAUTOCLAIM` after `reclaim_idle_ms`.
