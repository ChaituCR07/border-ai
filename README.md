# Border AI: AI Video Intelligence Platform

Real-time video analytics for existing CCTV/IP-camera infrastructure: detection, tracking, restricted-zone and line-crossing events, Automated Number Plate Recognition (ANPR), PostgreSQL-backed operational watchlists, facial biometric recognition, cross-camera person appearance Re-ID, declarative behaviour rules, composite threat scoring with explainable escalation alerts, and an investigation dashboard.

| **Week 1 Demo: Vision Pipeline & Spatial Tripwires** | **Week 2 Demo: Automated Number Plate Recognition (ANPR)** |
|:---:|:---:|
| ![Week 1 Demo](docs/images/week1_demo.gif) | ![Week 2 Demo](docs/images/week2_demo.gif) |
| *Real-time YOLOv8 detection, ByteTrack tracking, virtual tripwires & multi-zone boundaries.* | *License plate localization, PaddleOCR PP-OCRv6, character consensus voting & watchlist visual tagging.* |

---

## Current Status (Week 3 / Day 15 In Progress)

- **Week 1 (v0.1-week1) Complete:** Video/RTSP ingestion, YOLOv8 object detection, ByteTrack persistent tracking, multi-zone and virtual line spatial engine, live low-latency MJPEG streaming, and structured JSONL event logging.
- **Week 2 (Data & Streaming Architecture) Complete:** ANPR consensus engine (PaddleOCR PP-OCRv6 + layout validation), PostgreSQL 16 watchlist system with outage resilience fallback, biometric face detection & cross-camera Re-ID prototype, configurable declarative behaviour engine (rules R001–R005), multi-factor decaying threat scoring (0–100 explainable window), Redis Streams asynchronous event pipeline, and production relational schema (`003_core_schema.sql`) with idempotent PostgreSQL event sinks.
- **Week 3 (Productization & Dashboards) In Progress:**
  - **Day 15 Complete (Backend REST APIs - Node.js + TypeScript):** Production Fastify v5 REST API (Node.js 22 LTS + TypeScript) with schema-first Zod validation, handwritten parameterized SQL via node-postgres, keyset cursor pagination with microsecond timestamp fidelity (ADR 0015), strict data ownership (ADR 0014), atomic idempotent alert acknowledgement and non-biometric watchlist guard (ADR 0016), zero-filled time-series analytics, safe evidence snapshot serving, automated OpenAPI 3.0 documentation (`/docs`), and a 48-test suite covering unit, dual-backend repository contracts, Fastify routes, real PostgreSQL integration, and cross-language Python sink -> PostgreSQL -> Fastify REST API verification.
  - **Day 16 (Upcoming):** Live Operator Command Dashboard (Vite + React + TypeScript + TanStack Query + CSS Tokens).
  - **Day 17 (Upcoming):** WebSocket Server & Real-time Live Alert Feed.
  - **Day 18 (Upcoming):** Forensic Search & Investigation Workbench.
  - **Day 19 (Upcoming):** Cross-Camera Journey Correlation & Trajectory Reconstruction.
  - **Day 20 (Upcoming):** Alert Notification Engine (Webhook, Email, Audit).
  - **Day 21 (Upcoming):** Week 3 Integration, Performance Soak & Milestone Review.

---

## What It Does

- **Multi-Camera Ingestion:** Thread-per-camera ingestion from RTSP streams and video files with auto-reconnect, FPS pacing, and offline backpressure.
- **Detection & Tracking:** Real-time YOLOv8 person/vehicle detection paired with ByteTrack persistent ID tracking across camera frames.
- **Spatial Analytics Engine:** Config-driven restricted zones and tripwires supporting `ENTER`, `EXIT`, `DWELL`, `LOITERING`, and directional `LINE_CROSSING` events with hysteresis and duplicate suppression.
- **ANPR Engine:** Automated plate crop extraction, CLAHE preprocessing, character recognition, positional OCR correction, and multi-frame voting with dynamic early stopping.
- **Operational Watchlist System:** Real-time PostgreSQL lookup for `VEHICLE`, `PLATE`, `PERSON`, and `FACE` entities.
  - Scored matches ($0\text{--}100$) based on OCR read confidence and substitution quality.
  - OCR-aware near matching: look-alike substitutions (`B/8`, `O/0`, `1/I`, `S/5`, `Z/2`) cost 0.5; standard substitutions cost 1.0.
  - Dynamic visual flagging: watchlisted targets render with **red bounding boxes**, risk tags (`WATCHLIST HIGH`), and screen alert banners.
  - Outage resilience: seamless fallback to an in-memory snapshot during database drops, with automatic queued hit flushing upon reconnection.
- **Biometric Face Watchlist & Cross-Camera Re-ID:**
  - Face crop extraction, alignment, and 128-d L2-normalized embedding (OpenCV YuNet + SFace).
  - Multi-frame track aggregation with consistency validation to prevent tracker ID swap errors.
  - Cross-camera person appearance correlation emitting `REID_MATCH` candidates (`= CAM_001 #12?`).
  - Privacy safeguards: numeric embeddings only, strictly consent-gated enrollment, and human review defaults.
- **Configurable Behaviour Analysis Engine:**
  - Evaluates spatial, temporal, classification, OCR, and watchlist conditions per active track.
  - Firing management with `rearm_s` and `cooldown_s` to eliminate alert flooding while preserving zone and crossing context.
  - Generates self-explaining behaviour alerts (`details.reasons`) with threat points for downstream scoring.
  - Example Rule:
    ```json
    {
      "rule_id": "R005",
      "name": "Unauthorized Vehicle in Restricted Zone After Hours",
      "event_type": "UNAUTHORIZED_VEHICLE_AFTER_HOURS",
      "conditions": [
        {"type": "object", "value": ["car", "truck", "bus", "motorcycle"]},
        {"type": "zone", "zone_type": "restricted"},
        {"type": "time", "between": ["22:00", "05:00"]},
        {"type": "plate", "authorized": false}
      ],
      "action": {"severity": "CRITICAL", "score": 40}
    }
    ```
- **Composite Threat Scoring & Alert Escalation Engine:**
  - Synthesizes geometric observations, identity hits, and behaviour violations into an aggregate 0–100 threat score and 4-tier alert level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - **Decaying Sliding Window:** Active evidence decays after 10 minutes (`window_s: 600s`); repeating observations refresh the expiry timer without compounding points.
  - **Plate-Based Track Merging:** Automatically merges fragmented tracks for the same vehicle once a license plate is recognized, preserving score history across tracker ID swaps.
  - **Zero Double-Counting:** Smart exclusion rules (`excluded_by: ["direction_violation"]`) ensure multi-trigger incidents (such as wrong-way tripwires) count accurately.
  - **Review Multipliers:** Unconfirmed/review-grade detections receive half points (`status_multiplier: 0.5`).
  - **Escalation-Only Alerts:** Alerts are emitted strictly upon initial score threshold crossing or level increases, with automated quiet-period re-arming (`rearm_s: 300s`).
  - **Pre-Annotation Evidence Snapshots:** Captured pre-rendering and stored in `outputs/runs/<run_id>/snapshots/<alert_id>.jpg` for visual verification and operator review.
  - **Example THREAT_ALERT Event:**
    ```json
    {
      "type": "THREAT_ALERT",
      "severity": "HIGH",
      "threat_score": 60,
      "track_id": 3,
      "rule": {"id": "THREAT", "kind": "threat", "type": "high"},
      "details": {
        "level": "HIGH",
        "priority": "HIGH",
        "previous_level": "MEDIUM",
        "escalation": true,
        "summary": "HIGH (60/100): Restricted zone entry +30, Virtual line crossing +20, After-hours movement +10",
        "snapshot_path": "snapshots/3f2a1b0c.jpg",
        "contributions": [
          {"kind": "zone_violation", "label": "Restricted zone entry", "points": 30},
          {"kind": "line_crossing", "label": "Virtual line crossing", "points": 20},
          {"kind": "after_hours", "label": "After-hours movement", "points": 10}
        ]
      }
    }
    ```

- **Backend REST API Service (Node.js + TypeScript + Fastify v5):**
  - **Schema-First Type Safety:** Powered by Fastify v5 and `fastify-type-provider-zod` with strict request/response validation, automated OpenAPI 3.0 export, and Swagger UI at `/docs`.
  - **Strict Data Ownership (ADR 0014):** Python AI Engine owns writes to `events`, `detections`, and `vehicles`. Node.js API acts as a read-mostly consumer with exclusive write ownership of `api_audit_log` and state transitions on `alerts`.
  - **Keyset Cursor Pagination (ADR 0015):** High-throughput $O(1)$ tuple pagination on `(timestamp DESC, event_id DESC)` eliminating page drift during live surveillance. Preserves microsecond `timestamptz` precision via custom type parsers.
  - **Idempotent Alert Lifecycle (ADR 0016):** Atomic `PATCH /api/alerts/:id/acknowledge` guarantees single-winner acknowledgement across concurrent operators without duplicate audit rows or state corruption.
  - **Privacy-Preserving Watchlists:** Non-biometric REST boundary rejecting any face embeddings or raw images. Full vehicle plate normalisation matching Python ANPR logic, and mandatory consent references for persons.
  - **Operational Intelligence & Zero-Filled Analytics:** Hourly and daily time-series aggregation zero-filled across missing intervals, camera operational counters, threat score distribution histograms, and safe sandboxed snapshot evidence serving (`/api/snapshots/*`).

- **Administrative & Operational CLI:** Comprehensive CLI tools for schema migration, synthetic demo seeding, entity curation, dry-run plate checks, consent-gated face enrollment, threat arithmetic calculation, rules validation, and offline event replay.

---

## Architecture

```text
Cameras / RTSP / Video Files
        ↓
Video Ingestion (thread per camera, bounded queues, FPS pacing)
        ↓
Batched Detection (YOLOv8) ──► Multi-Camera Tracker (ByteTrack) ──► Spatial Rules (Zones, Lines)
        ↓                                                                    ↓
ANPR Engine (PaddleOCR + Consensus)                           Events: ENTER / EXIT / LOITERING /
        ↓                                                             LINE_CROSSING (JSONL)
Watchlist Engine (PostgreSQL / In-Memory Snapshot Fallback)                  ↓
        ↓                                                     Events: WATCHLIST_MATCH (Plate)
Identity Engine (Async Face & Appearance Re-ID Worker)                       ↓
        ↓                                                     Events: WATCHLIST_MATCH (Face)
        ↓                                                     Events: REID_MATCH (Candidate)
        ↓                                                                    ↓
Behaviour Engine (Declarative Rules R001–R005) ───────────────► Events: ZONE_VIOLATION, ...
        ↓                                                                    ↓
Threat Scoring Engine (Decaying Window, Plate Merging) ───────► Events: THREAT_ALERT (JSONL)
        ↓                                                                    ↓
Visualizer Overlay (Bounding Box Colors, T<score> Labels, Banners)   Pre-Annotation Snapshots (.jpg)
        ↓                                                                    ↓
Redis Streams Event Bus (v1 Envelope) ─────────────────────────► PostgreSQL 16 (003_core_schema.sql)
                                                                             ↓
                                                                 Node.js 22 REST API (Fastify v5 + Zod)
                                                                 - Keyset Pagination & Microsecond Ts
                                                                 - Idempotent Alert Transitions
                                                                 - Zero-Filled Analytics & Snapshots
                                                                             ↓
                                                                 Day 16 Command Dashboard (Vite + React)
```

---

## Quick Start

### 1. Prerequisites & Environment
Ensure Docker is installed, then launch the background services (PostgreSQL 16 & Redis 7):
```bash
docker compose up -d
```

Set up your Python virtual environment (Python 3.11 recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e video-ingestion
pip install -r ai-engine/requirements.txt
pip install -r ai-engine/requirements-anpr.txt  # Optional: Installs PaddleOCR & dependencies
```

### 2. Initialize Watchlist Database
Run the idempotent migrations (001 and 002) and seed synthetic demo data:
```bash
python ai-engine/scripts/db_migrate.py up
python ai-engine/scripts/watchlist_cli.py import configs/watchlist_demo.csv
```

### 3. Launch Backend REST API (Node.js + Fastify)
Start the typed REST API service exposing cameras, events, alerts, and analytics:
```bash
cd backend
npm install
npm run dev
```
Interactive Swagger documentation will be available at `http://localhost:4000/docs` and `/openapi.json`.

### 3. Run Pipeline with Live Demo & Threat Scoring
Execute the end-to-end pipeline with simulated night clock and threat scoring:
```bash
cd ai-engine
python scripts/run_pipeline.py \
    --source ../datasets/videos/person_walking.mp4 \
    --camera-id CAM_001 \
    --clock-start 2026-10-12T02:13:00
```
Outputs (annotated video, events log, run telemetry, and evidence snapshots) will be saved in `outputs/runs/<RUN_TIMESTAMP>/`.

---

## Management & Evaluation CLI Tools

### Threat Scoring & Rules
```bash
# Validate Plan Scenario 1 and Scenario 2 arithmetic without video
python ai-engine/scripts/threat_calc.py --plan

# Test arbitrary threat evidence combinations
python ai-engine/scripts/threat_calc.py watchlist_vehicle:alert zone_violation direction_violation after_hours

# Replay recorded events.jsonl through the scorer with new parameters
python ai-engine/scripts/score_replay.py --events outputs/runs/<run_id>/events.jsonl --tick 1.0

# Verify syntax and consistency between behaviour rules and scoring sources
python ai-engine/scripts/rules_check.py
```

### Plate Watchlist
```bash
# Check what would happen if a plate is recognized
python ai-engine/scripts/watchlist_cli.py check KA01AB1234 --confidence 0.91

# Inspect hit history and audit trails
python ai-engine/scripts/watchlist_cli.py hits --limit 10
python ai-engine/scripts/watchlist_cli.py audit --limit 10
```

### Face Enrollment & Smoke Test
```bash
# Test face detection and embedding on image pairs
python ai-engine/scripts/face_smoke_test.py --image photo1.jpg --image2 photo2.jpg

# Enrol a consenting individual (consent confirmation mandatory)
python ai-engine/scripts/face_enroll.py \
    --folder path/to/subject_photos/ \
    --identifier subject-001 \
    --name "Volunteer A" \
    --risk LOW \
    --consent-confirmed

# Run genuine vs. impostor evaluation
python ai-engine/scripts/face_eval.py --folder datasets/faces/

# Evaluate cross-camera Re-ID rank-k retrieval
python ai-engine/scripts/reid_eval.py --folder datasets/reid/ --embedder color_layout
```

---

## Testing & Quality Assurance

The platform features a rigorous testing suite designed to ensure zero false regressions, pipeline stability, and database resilience:

### Test Suite Execution
```bash
# Run all tests across the repository (501 tests)
cd ai-engine && pytest -v && cd .. && pytest video-ingestion/tests -v

# Run fast unit, contract, and scenario tests (no database required)
cd ai-engine && pytest -m "not db and not slow" -v

# Run PostgreSQL-backed database tests
cd ai-engine && pytest -m db -v

# Run with code coverage report
cd ai-engine && pytest -m "not slow" --cov=app --cov-report=term-missing
```

### Test Coverage Summary: 549 Passed (100% Green)
- **`backend` (48 passed, 0 skipped - 100% Green):**
  - **Unit Tests (`tests/unit/`):** Pure function tests for time parsing, base64url cursor encoding/decoding, cross-language plate normalisation fixtures, and AppError classes.
  - **Contract Tests (`tests/contract/`):** Behavioral parity tests verifying identical contract execution across `InMemory` and `Pg` repositories for cameras and watchlists.
  - **Route Tests (`tests/routes/`):** Comprehensive `app.inject()` suites covering cameras CRUD, events keyset pagination, atomic alert acknowledgement, biometric field rejection, analytics buckets, and path traversal security.
  - **Database Integration Tests (`tests/integration/`):** Real PostgreSQL 16 queries, microsecond tuple cursor comparisons, and 10-worker concurrent acknowledge race conditions.
  - **Cross-Language E2E Tests (`tests/e2e/`):** Python `PostgresEventSink` -> PostgreSQL -> Fastify REST API query verification.
- **`ai-engine` (493 passed, 33 db-skipped when offline):**
  - **Unit Tests:** Plate normalization, OCR distances, face quality gate, yaw angle ratios, L2 normalization, embedding cosine similarities, scoring arithmetic, decaying window expiry, and configuration validation.
  - **Dual-Backend Contract Tests:** Identical behavioral verification run against both `InMemoryWatchlistRepo` and `PostgresWatchlistRepo` for plates, face embeddings, and hit history.
  - **Database & Schema Tests:** Migration idempotency (001 and 002), check constraints, partial unique active indexes, and connection failure handling.
  - **Service & Worker Tests:** Asynchronous queue processing, per-camera cooldown suppression, status upgrades, hit persistence, multi-frame consistency fusion, and Re-ID gallery candidate matching.
  - **Behaviour Engine Tests:** Declarative rule validation, spatial/temporal/classification condition evaluators, episode deduplication, and simulated clock runs.
  - **Threat Scoring Tests:** 0–100 score capping, order independence, monotonicity, decaying sliding window, plate-based track merging, and escalation-only alerting.
  - **Pipeline Integration Tests:** Multi-threaded pipeline execution integrating detector, tracker, ANPR, watchlist, identity service, behaviour rules, threat scoring, and pre-annotation snapshots.
  - **Scale Tests:** Verified lookup correctness with **10,000 active entries**.
- **`video-ingestion` (8 tests):** Frame reading, timestamp synchronization, frame skipping, aspect-ratio resizing, source looping, and offline backpressure queue management.
- **CI/CD:** Automated via GitHub Actions ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)) with an automated PostgreSQL 16 container service.

### Verified Demos & Acceptance Results
- **Plan Scenario 1 (Restricted Area at Night):**
  - Incident: A person approaches, crosses the virtual tripwire (+20), and enters the restricted zone (+30) at 02:13 AM (+10 after-hours).
  - Outcome: **Threat Score: 60, Level: HIGH**. Alert sequence: `LOW` (10) → `MEDIUM` (40) → `HIGH` (60).
  - Verified in `ai-engine/tests/test_threat_scenarios.py` and via live pipeline with `--clock-start 2026-10-12T02:13:00`.
- **Plan Scenario 2 (Watchlisted Vehicle Intrusion):**
  - Incident: A watchlisted vehicle (+40) enters the restricted zone (+30), crosses the virtual tripwire the wrong way (+20 direction violation, crossing excluded), at night (+10 after-hours), triggering the multi-suspicious bonus (+10).
  - Outcome: **Raw Score: 110, Capped Threat Score: 100, Level: CRITICAL**.
  - Verified in `ai-engine/tests/test_threat_scenarios.py` through the real geometry, track store, and rule engines.
- **Plan Tests 1–6:**
  - *Test 1:* Normal pedestrian walk produces zero unauthorized alerts.
  - *Test 2:* Person loitering inside zone > 60s raises `LOITERING_VIOLATION`.
  - *Test 3:* Unlisted vehicle produces zero watchlist alerts.
  - *Test 4:* Watchlisted plate `KA01AB1234` immediately raises a `WATCHLIST_MATCH` alert.
  - *Test 5:* Vehicle traveling in authorized direction raises zero direction violations.
  - *Test 6:* Daytime movement raises zero after-hours activity violations.
- **Ground Truth Verification:**
  - Automated comparison scripts verify outputs against curated ground-truth datasets in [`docs/ground_truth/`](docs/ground_truth/): `threat_person_walking.json`, `behaviour_person_walking.json`, `anpr_vehicles.json`, and `anpr_vehicle_track.json`.

---

## Benchmark Highlights

Detailed methodology and measurements are recorded in [docs/benchmarks.md](docs/benchmarks.md):

| Component | Operation | Result | Notes |
|---|---|---|---|
| **YOLOv8n Inference** | Single Camera FPS | **19.9 FPS** | CPU FP32 (`640px`), zero dropped frames |
| **Multi-Camera Batch** | Dual Camera FPS | **10.4 FPS / cam** | Dynamic batching (avg batch 1.97) |
| **ANPR Inference** | Recognition Latency | **~271.6 ms** | PP-OCRv6 on CPU, run asynchronously |
| **ANPR Throughput** | Worker Capacity | **~3.3 reads/s** | Early consensus stopping limits reads to 3-4/car |
| **Watchlist Lookup** | Exact Hit (10k entries)| **0.78 ms** | Sub-millisecond indexed lookup |
| **YuNet Face Detect** | Upper Crop (128x128 px)| **8.5 ms** | OpenCV DNN CPU execution |
| **SFace Face Embed** | Aligned (112x112 px) | **12.4 ms** | 128-d L2-normalized float32 vector |
| **ColorLayout Re-ID** | Person Crop (64x128 px)| **1.8 ms** | Gray-world normalized HSV histograms |
| **Identity Capacity** | Worker Throughput | **~44 crops/s** | Sustains multi-camera pedestrian tracking |

---

## Responsible Use & Privacy Policy

- **Biometrics Policy ([docs/privacy.md](docs/privacy.md)):** Face matching and Re-ID capabilities are **disabled by default**. They must only be operated in authorized environments with consenting participants or permitted research datasets.
- **No Third-Party PII:** All development, testing, and benchmark datasets utilize strictly synthetic license plates and synthetic identity references.
- **Zero Image Storage:** Only mathematical embeddings are persisted. Raw facial images and crops are never stored.
- **Access Control:** Identity resolution requires authenticated role permissions (Investigator/Admin).

---

## Roadmap

- [x] **Week 1 (Days 1–7) Ingestion & Spatial Foundation:** Thread-per-camera ingestion (RTSP/file), YOLOv8 object detection, ByteTrack tracking, multi-zone and tripwire spatial analytics, live low-latency MJPEG streaming, and structured JSONL event logging.
- [x] **Week 2 (Days 8–14) Data & Streaming Architecture:** ANPR engine (PaddleOCR + layout syntax rules + multi-frame consensus), PostgreSQL 16 watchlist system with outage resilience fallback, biometric face detection & appearance Re-ID prototype, configurable declarative behaviour engine (rules R001–R005), multi-factor decaying threat scoring (0–100 explainable window), Redis Streams asynchronous event pipeline, and production relational schema (`003_core_schema.sql`) with idempotent PostgreSQL event sinks.
- [ ] **Week 3 (Days 15–21) Productization & Dashboards:**
  - [x] **Day 15 — Backend REST APIs:** Production Fastify v5 REST API (Node.js 22 LTS + TypeScript) with schema-first Zod validation, handwritten parameterized SQL via node-postgres, keyset cursor pagination with microsecond timestamp fidelity (ADR 0015), strict data ownership (ADR 0014), atomic idempotent alert acknowledgement and non-biometric watchlist guard (ADR 0016), zero-filled time-series analytics, safe evidence snapshot serving, automated OpenAPI 3.0 documentation (`/docs`), and a 48-test suite (unit, contract parity, Fastify routes, PostgreSQL integration, and cross-language Python sink -> PostgreSQL -> Fastify REST API verification).
  - [ ] **Day 16 — Live Operator Command Dashboard:** Real-time web surveillance interface using Vite + React 18/19 + TypeScript + TanStack Query with live camera grid status, live video feed integration via MJPEG gateway, threat score counters, alert feed with instant operator acknowledge actions, and trend charts.
  - [ ] **Day 17 — WebSocket Live Alert Server & Push Broadcasting:** Low-latency alert distribution via Fastify WebSocket and Redis pub/sub, broadcasting new threat detections and live acknowledgement sync across multi-operator terminals in sub-second time.
  - [ ] **Day 18 — Forensic Search & Investigation Workbench:** Multi-parametric historical investigation portal supporting fuzzy plate queries, multi-camera time range filters, track journey inspect modal, synchronized video replay, and PDF/JSON incident dossier export.
  - [ ] **Day 19 — Cross-Camera Journey Correlation & Trajectory Reconstruction:** Multi-camera re-identification integration, automated spatial-temporal vehicle/pedestrian trajectory mapping, dwell-time analysis between camera checkpoints, and interactive journey path visualization.
  - [ ] **Day 20 — Multi-Channel Alert Dispatcher & External Notifications:** Automated escalation engine dispatching high/critical priority alerts via Webhooks, Email (SMTP), and operator audio triggers with rate limiting, retry backoff, and full dispatch audit logging.
  - [ ] **Day 21 — Week 3 Milestone Review & Stress Soak Verification:** End-to-end integration across all 6 simulated camera streams, frontend dashboard soak testing, API latency profiling under 100k+ event volume, and Week 3 release tagging (`v0.3-week3`).
- [ ] **Week 4 (Days 22–28) Hardening, Security & Deployment:** JWT authentication & RBAC, multi-camera soak testing, end-to-end integration, Docker packaging, and hardware pilot.
