# AI Engine (`ai-engine`)

The **AI Engine** is the core computer vision and intelligence processing subsystem of the Border AI platform. It ingests frames emitted by `video-ingestion`, performs real-time object detection and multi-object tracking, calculates spatial zone and tripwire intrusions, evaluates behavioral rules, matches against operational watchlists, performs facial biometric and person appearance Re-ID, calculates multi-factor composite threat scores, and generates structured security observations and escalation alerts.

---

## 1. Directory Structure of AI Engine

```text
ai-engine/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI REST application entrypoint (:8000)
│   ├── config.py              # Environment variable (.env) and YAML config loader
│   ├── api/                   # REST API routes and endpoints
│   ├── detection/             # Object detection wrappers (YOLOv8)
│   ├── tracking/              # Multi-object tracking algorithms (ByteTrack)
│   ├── analytics/             # Spatial geometry (polygons, lines, loitering)
│   ├── pipeline/              # Multi-threaded frame processing coordinator, visualizer, & snapshots
│   ├── schemas/               # Pydantic data schemas (Detection, Track, Event)
│   ├── utils/                 # Geometry algorithms, timing, and logging
│   ├── anpr/                  # Automatic Number Plate Recognition (PaddleOCR, consensus voting)
│   ├── watchlist/             # PostgreSQL 16 operational watchlist repository & matcher
│   ├── identity/              # Face detection (YuNet), SFace embeddings, and Re-ID gallery
│   ├── behaviour/             # Declarative behaviour engine (rules R001–R005, episode contexts)
│   ├── threat/                # Multi-factor threat scoring engine (decay window, plate merge, alerts)
│   └── db/                    # PostgreSQL connection pools and schema migrations
├── models/                    # Pretrained weights (e.g., yolov8n.pt - gitignored)
├── scripts/                   # Operational CLI tools & offline evaluation utilities
│   ├── run_pipeline.py        # End-to-end multi-threaded analytics pipeline runner
│   ├── threat_calc.py         # Arithmetic validator for hypothetical threat combinations
│   ├── score_replay.py        # Offline event log threat scoring replay and tuning tool
│   ├── rules_check.py         # Config validator for behaviour rules and scoring sources
│   ├── replay_behaviour.py    # Offline behaviour rule replay without GPU
│   ├── check_events.py        # Ground-truth event count and type verification
│   ├── watchlist_cli.py       # Watchlist inspection and CRUD CLI
│   ├── face_enroll.py         # Consent-gated face biometric enrollment utility
│   ├── face_eval.py           # Genuine vs. impostor facial verification evaluation
│   └── reid_eval.py           # Cross-camera appearance Re-ID rank-k evaluation
├── tests/                     # 493+ automated unit, scenario, contract, and integration tests
├── Dockerfile                 # Container specification for GPU/CPU inference
└── requirements.txt           # Python dependencies (PyTorch, Ultralytics, OpenCV, FastAPI)
```

---

## 2. Core Capabilities

### Object Detection & Tracking (Week 1)
- **Ultralytics YOLOv8:** Real-time object detection (`person`, `car`, `truck`, `bus`, `motorcycle`, `bicycle`).
- **ByteTrack:** Maintains persistent track IDs, bounding boxes, and velocity trajectories across camera frames.

### Spatial Analytics Engine (Week 1)
- **Restricted Zones & Virtual Lines:** Point-in-polygon containment and tripwire intersection algorithms with hysteresis and entry/exit/dwell state machines.

### ANPR Engine (Day 8)
- **PaddleOCR (PP-OCRv6):** Automated license plate localization, CLAHE preprocessing, Indian RTO and generic format normalization, and multi-frame consensus voting.

### Operational Watchlist System (Day 9)
- **PostgreSQL 16 & In-Memory Dual Repository:** Real-time lookup for vehicles, plates, and persons.
- **OCR-Aware Near Matcher:** Substitutes look-alikes (`B/8`, `O/0`, `1/I`) with fractional edit penalties.
- **Resilience Snapshot:** In-memory fallback during database outages with automatic queued hit synchronization.

### Facial Biometrics & Appearance Re-ID (Day 10)
- **YuNet & SFace:** Face detection, quality gating (pose, blur, illumination), and 128-d L2-normalized cosine similarity matching.
- **ColorLayout Appearance Re-ID:** Multi-camera pedestrian candidate matching across occlusions.

### Behaviour Analysis Engine (Day 11)
- **Declarative Rule Engine:** Evaluates spatial, temporal, track-history, and classification conditions (`configs/rules.json`).
- **Core Rules:** Restricted zone intrusion (`R001`), wrong direction (`R002`), loitering > 60s (`R003`), after-hours activity (`R004`), and night-time unauthorized vehicle entry (`R005`).

### Threat Scoring & Alert Elevation Engine (Day 12)
- **0–100 Composite Threat Score:** Aggregates geometric observations, watchlist hits, and behaviour violations with configurable weights.
- **Temporal Decay:** 10-minute sliding window (`window_s: 600s`) decays stale evidence; repeating evidence refreshes expiry.
- **Plate-Based Track Merging:** Merges fragmented tracks sharing a recognized plate to maintain persistent threat history.
- **Escalation Alerts:** Emits prioritized `THREAT_ALERT` events strictly upon score threshold crossing or level increases (`LOW` -> `MEDIUM` -> `HIGH` -> `CRITICAL`).
- **Evidence Snapshots:** Captures clean pre-annotation JPEG frames stored in `outputs/runs/<run_id>/snapshots/`.

---

## 3. Operational Tooling

### Threat Calculator
Test and verify arbitrary combinations of evidence:
```bash
python scripts/threat_calc.py --plan
python scripts/threat_calc.py watchlist_vehicle:alert zone_violation direction_violation after_hours
```

### Threat Score Replay
Replay recorded runs with new scoring parameters or weight configurations:
```bash
python scripts/score_replay.py --events ../outputs/runs/<run_id>/events.jsonl --tick 1.0
```

### Rules & Scoring Consistency Checker
Verify syntax and consistency between behaviour rules and scoring sources:
```bash
python scripts/rules_check.py
```

### End-to-End Pipeline Execution
Run the complete pipeline with simulated clocks and threat overlays:
```bash
python scripts/run_pipeline.py \
    --source ../datasets/videos/person_walking.mp4 \
    --camera-id CAM_001 \
    --clock-start 2026-10-12T02:13:00
```

---

## 4. Testing & Verification

The `ai-engine` test suite contains **493 passing tests** (100% green) protecting every tier:
```bash
# Run all tests (skipping slow scale tests and offline DB tests)
pytest -m "not db and not slow" -v

# Run threat scoring tests specifically
pytest tests/test_threat_config.py tests/test_threat_scoring_math.py tests/test_threat_scorer.py tests/test_threat_scenarios.py tests/test_pipeline_threat.py tests/test_threat_tools.py -v

# Run full test suite including database tests (requires PostgreSQL container)
pytest -v
```
