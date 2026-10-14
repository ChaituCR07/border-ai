# Border AI: AI Video Intelligence Platform

Real-time video analytics for existing CCTV/IP-camera infrastructure: detection,
tracking, restricted-zone and line-crossing events, Automated Number Plate Recognition (ANPR),
PostgreSQL-backed operational watchlists, and (in progress) face/appearance Re-ID,
behaviour rules, threat scoring, and an investigation dashboard.

![demo](docs/images/week1_demo.gif)

---

## Current Status (Day 9 Complete)

- **Week 1 (v0.1-week1) Complete:** Video/RTSP ingestion, YOLOv8 object detection, ByteTrack tracking, multi-zone and virtual line spatial engine, live MJPEG streaming, and structured JSONL event logging.
- **Week 2 (Intelligence Layer) In Progress:**
  - **Day 8 Complete (ANPR):** Plate localization, PaddleOCR (PP-OCRv6), positional syntax checking (Indian RTO & generic format validation), and multi-frame character/string consensus voting.
  - **Day 9 Complete (Watchlist & Testing Suite):** PostgreSQL 16 watchlist system with dual-backend repositories (PostgreSQL & in-memory), OCR-tolerant near matching, track overlay visual alerting (red box & banner), in-memory snapshot outage resilience, and a comprehensive 284-test verification suite.
  - **Upcoming (Days 10–14):** Face detection & cross-camera Re-ID, behavioral analytics, multi-factor threat scoring, Redis Streams integration, and unified schema persistence.

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
  - Privacy-first design: human identities are omitted from public event streams and resolved only by authorized roles.
  - Outage resilience: seamless fallback to an in-memory snapshot during database drops, with automatic queued hit flushing upon reconnection.
- **Administrative CLI:** Comprehensive CLI tool for schema migration, synthetic demo seeding, entity curation, CSV import/export, and dry-run plate checks.

---

## Architecture

```text
Cameras / RTSP / Video files
        ↓
Video Ingestion (thread per camera, bounded queues, FPS pacing)
        ↓
Batched Detection (YOLOv8) ──► Multi-Camera Tracker (ByteTrack) ──► Rule Engine (Zones, Lines)
        ↓                                                                    ↓
ANPR Engine (PaddleOCR + Consensus)                           Events: ENTER / EXIT / LOITERING /
        ↓                                                             LINE_CROSSING (JSONL)
Watchlist Engine (PostgreSQL / In-Memory Snapshot Fallback)                  ↓
        ↓                                                     Events: WATCHLIST_MATCH (JSONL)
Annotated Video (Red Boxes / Banners) + Live MJPEG Streams                   ↓
                                                              Plate Records: plates.jsonl (JSONL)
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
pip install -r ai-engine/requirements-anpr.txt  # Installs PaddleOCR & dependencies
```

### 2. Initialize Watchlist Database
Run the idempotent migration and seed synthetic demo data:
```bash
python ai-engine/scripts/db_migrate.py
python ai-engine/scripts/watchlist_cli.py seed-demo
python ai-engine/scripts/watchlist_cli.py list
```

### 3. Run the Pipeline
Run an offline video clip or live RTSP camera stream:
```bash
cd ai-engine
python scripts/run_pipeline.py --source ../datasets/videos/vehicles.mp4 --camera-id CAM_002
```
Outputs appear in `outputs/runs/<run_id>/`:
- Annotated MP4 video (`CAM_002.mp4`) with bounding boxes, trajectory trails, and watchlist alerts.
- Structured event stream (`events.jsonl`).
- ANPR plate consensus log (`anpr/plates.jsonl`).
- Run metrics and configuration manifest (`summary.json`, `manifest.json`).

---

## Watchlist Management CLI

The watchlist can be managed directly via `ai-engine/scripts/watchlist_cli.py`:

```bash
# Check what would happen if a plate is recognized
python ai-engine/scripts/watchlist_cli.py check KA01AB1234 --confidence 0.91
# Output: KA01AB1234: exact match with #1 (HIGH), distance 0.0, score 91, status alert

# Check near match (one digit off - triggers human review)
python ai-engine/scripts/watchlist_cli.py check KA01AB1284 --confidence 0.91
# Output: KA01AB1284: near match with #1 (HIGH), distance 1.0, score 73, status review

# Add, update, or remove entries
python ai-engine/scripts/watchlist_cli.py add --type VEHICLE --identifier DL01AB9999 --name "Suspect Vehicle" --risk HIGH
python ai-engine/scripts/watchlist_cli.py remove 1 --reason "Investigation closed"

# Inspect hit history and audit trails
python ai-engine/scripts/watchlist_cli.py hits --limit 10
python ai-engine/scripts/watchlist_cli.py audit --limit 10
```

---

## Testing & Quality Assurance

The platform features a rigorous testing suite designed to ensure zero false regressions, pipeline stability, and database resilience:

### Test Suite Execution
```bash
# Run all tests across the repository
cd ai-engine && pytest -v && cd .. && pytest video-ingestion/tests -v

# Run fast unit and contract tests (no database required)
cd ai-engine && pytest -m "not db and not slow" -v

# Run PostgreSQL-backed database tests
cd ai-engine && pytest -m db -v

# Run with code coverage report
cd ai-engine && pytest -m "not slow" --cov=app --cov-report=term-missing
```

### Test Coverage Summary: 284 Passed (100% Green)
- **`ai-engine` (276 tests):**
  - **Unit Tests:** Plate normalization, OCR distances, confusable look-alike matrices, scoring thresholds, and config validation.
  - **Dual-Backend Contract Tests:** Identical behavioral verification run against both `InMemoryWatchlistRepo` and `PostgresWatchlistRepo`.
  - **Database & Schema Tests:** Migration idempotency, check constraints, partial unique active indexes, and connection failure handling.
  - **Service & Worker Tests:** Asynchronous queue processing, per-camera cooldown suppression, status upgrades, and hit persistence.
  - **Plan Acceptance Tests:**
    - *Test 3:* Unlisted vehicle produces zero watchlist alerts.
    - *Test 4:* Watchlisted plate `KA01AB1234` immediately raises an alert event and flags the video.
    - *Scenario 2:* Watchlisted vehicle tracking and risk level correlation.
  - **Outage Resilience Tests:** Verified uninterrupted alert processing during database failure using snapshot fallbacks, with automated hit queuing and flushing.
  - **Pipeline Integration Tests:** End-to-end multi-threaded pipeline runs combining tracker, ANPR, rule engine, and watchlist.
  - **Scale Tests:** Verified lookup correctness with **10,000 active entries**.
- **`video-ingestion` (8 tests):** Frame reading, timestamp synchronization, frame skipping, aspect-ratio resizing, source looping, and offline backpressure queue management.
- **CI/CD:** Automated via GitHub Actions ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)) with an automated PostgreSQL 16 container service.

---

## Benchmark Highlights

Detailed methodology and measurements are recorded in [docs/benchmarks.md](docs/benchmarks.md):

| Component | Metric | Result | Notes |
|---|---|---|---|
| **YOLOv8n Inference** | Single Camera FPS | **19.9 FPS** | CPU FP32 (`640px`), zero dropped frames |
| **Multi-Camera Batch** | Dual Camera FPS | **10.4 FPS / cam** | Dynamic batching (avg batch 1.97) |
| **ANPR Inference** | Recognition Latency | **~271.6 ms** | PP-OCRv6 on CPU, run asynchronously |
| **ANPR Throughput** | Worker Capacity | **~3.3 reads/s** | Early consensus stopping limits reads to 3-4/car |
| **ANPR Accuracy** | Character Accuracy | **93.9%** | Evaluated on synthetic & staged crops |
| **Watchlist Lookup** | Exact Hit (1k entries) | **0.55 ms** | Indexed PostgreSQL lookup |
| **Watchlist Lookup** | Exact Hit (10k entries)| **0.78 ms** | Sub-millisecond latency |
| **Watchlist Lookup** | Near Miss (10k entries)| **1.85 ms** | Filtered candidate pool + Python distance |

---

## Event Schema Examples

### 1. Spatial Rule Event (`LINE_CROSSING`)
```json
{
  "event_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "camera_id": "CAM_001",
  "timestamp": "2026-10-08T05:23:41.120Z",
  "frame_id": 340,
  "type": "LINE_CROSSING",
  "track_id": 17,
  "direction": "IN",
  "confidence": 0.912,
  "object_class": "person",
  "bbox": [140.0, 110.0, 180.0, 170.0],
  "rule_id": "L1",
  "rule_name": "Entry Line",
  "rule_kind": "line",
  "rule_type": "tripwire"
}
```

### 2. Watchlist Match Event (`WATCHLIST_MATCH`)
```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "camera_id": "CAM_002",
  "timestamp": "2026-10-14T15:30:10.500Z",
  "frame_id": 450,
  "type": "WATCHLIST_MATCH",
  "track_id": 42,
  "plate": "KA01AB1234",
  "score": 91,
  "confidence": 0.91,
  "object_class": "car",
  "bbox": [120.0, 340.0, 480.0, 610.0],
  "rule_id": "WATCHLIST",
  "rule_name": "Watchlist match",
  "rule_kind": "watchlist",
  "rule_type": "vehicle",
  "details": {
    "plate": "KA01AB1234",
    "score": 91,
    "status": "alert",
    "review_required": false,
    "entry_id": 1,
    "entity_type": "VEHICLE",
    "risk_level": "HIGH",
    "match_type": "exact",
    "distance": 0.0,
    "matched_identifier": "KA01AB1234",
    "plate_confidence": 0.912,
    "also_matched": []
  }
}
```

---

## Repository Layout

- `ai-engine/`: Core analytics engine, YOLO detection, ByteTrack tracking, rule engine, ANPR service, watchlist service, and FastAPI server.
  - `app/anpr/`: Plate localization, PaddleOCR wrapper, format validation, and consensus voting.
  - `app/watchlist/`: Watchlist models, normalization, matcher, PostgreSQL/in-memory repositories, and background worker.
  - `app/db/`: Connection management and database migration runner.
  - `scripts/`: Operational tools (`run_pipeline.py`, `watchlist_cli.py`, `watchlist_simulate.py`, `watchlist_bench.py`, `db_migrate.py`).
  - `tests/`: 276 unit, contract, integration, and scenario acceptance tests.
- `video-ingestion/`: Video ingestion library, multi-camera manager, and RTSP reconnect sources.
- `database/migrations/`: SQL migration files (`001_watchlist.sql`).
- `configs/`: Declarative camera specifications, zones/lines config, and demo datasets (`watchlist_demo.csv`).
- `docs/`: Architectural Decision Records (ADRs 0001–0008), benchmark records, API contracts, testing guides, and watchlist documentation.

---

## Responsible Use & Privacy Policy

- **No Third-Party PII:** All development, testing, and benchmark datasets utilize strictly synthetic license plates and synthetic identity references.
- **Access Control:** Watchlist identity resolution requires authenticated role permissions (Investigator/Admin).
- **Compliance:** Deployment organizations are responsible for data retention, camera authorization, and jurisdictional surveillance compliance.

---

## Roadmap

- [x] **Week 1 (Days 1–7):** Ingestion, YOLOv8, ByteTrack, Spatial Zones & Lines, Stream API.
- [x] **Week 2 Day 8:** ANPR Engine (PaddleOCR PP-OCRv6 + positional layout rules + consensus voting).
- [x] **Week 2 Day 9:** PostgreSQL Watchlist System, OCR-aware near matcher, visual overlays, resilience fallback, and test suite.
- [ ] **Week 2 Day 10:** Face Detection & Appearance Embedding Re-ID prototype.
- [ ] **Week 2 Day 11–12:** Multi-camera behavioral correlation & composite threat scoring.
- [ ] **Week 2 Day 13–14:** Redis Streams event publishing & consolidated PostgreSQL persistence schema.
- [ ] **Week 3 (Days 15–21):** Node.js backend API, WebSocket alert broadcast, React surveillance dashboard.
- [ ] **Week 4 (Days 22–28):** Multi-camera soak testing, end-to-end integration, Docker packaging, and hardware pilot.
