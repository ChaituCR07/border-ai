# Testing Suite & Verification Strategy (`tests`)

The Border AI platform employs an extensive, multi-tiered testing suite comprising **501 automated tests** (100% passing) ensuring mathematical correctness, temporal stability, database contract parity, and zero regressions across all security analytics tiers.

---

## 1. Testing Architecture

| Layer | What it Proves | Key Test Files | Pytest Marker |
|---|---|---|---|
| **Unit & Utilities** | Geometry, OCR parsing, plate syntax, embeddings, normalization | `test_geometry.py`, `test_plate_format.py`, `test_consensus.py`, `test_watchlist_normalize.py`, `test_identity_core.py` | None |
| **Dual-Backend Contracts** | In-Memory and PostgreSQL repositories behave identically | `test_watchlist_repo_contract.py` | `db` (Postgres parameter) |
| **Database & Migrations** | Schema idempotency, check constraints, partial unique active indexes | `test_watchlist_db.py` | `db` |
| **Worker & Service Flow** | Background queues, thread safety, cooldowns, status upgrades, fallback | `test_anpr_service.py`, `test_watchlist_service.py`, `test_identity_service.py` | None |
| **Behaviour Engine** | Condition evaluation, spatial/temporal logic, episode deduplication | `test_behaviour_config.py`, `test_behaviour_conditions.py`, `test_behaviour_engine.py` | None |
| **Threat Scoring Math** | 0–100 cap, sliding window decay, double-counting exclusions, multi-bonus | `test_threat_config.py`, `test_threat_scoring_math.py`, `test_threat_scorer.py` | None |
| **Plan Scenarios (Acceptance)**| Real-engine execution of Plan Scenario 1 (60 HIGH), Scenario 2 (100 CRITICAL), Tests 1–6 | `test_behaviour_scenarios.py`, `test_watchlist_scenarios.py`, `test_threat_scenarios.py` | None |
| **Pipeline Integration** | Multi-threaded coordinator: Ingestion + Detection + Tracker + Rules + Scoring + Snapshots | `test_pipeline_integration.py`, `test_pipeline_anpr.py`, `test_pipeline_watchlist.py`, `test_pipeline_identity.py`, `test_pipeline_threat.py` | `integration` |
| **Operational Tools** | Calculator arithmetic, event replay, and configuration validators | `test_behaviour_tools.py`, `test_threat_tools.py` | None |
| **Video Ingestion** | Source decoders, FPS pacing, aspect resizing, thread backpressure | `video-ingestion/tests/test_sources.py` | None |

---

## 2. Running Tests

### Fast Feedback Loop (No Database Required)
Executes all unit, contract, behaviour, threat scoring, and scenario acceptance tests:
```bash
cd ai-engine
pytest -m "not db and not slow" -v
```

### Run Day 12 Threat Scoring Tests
```bash
cd ai-engine
pytest tests/test_threat_config.py \
       tests/test_threat_scoring_math.py \
       tests/test_threat_scorer.py \
       tests/test_threat_scenarios.py \
       tests/test_pipeline_threat.py \
       tests/test_threat_tools.py -v
```

### Run Full Platform Suite
```bash
cd ai-engine && pytest -v && cd .. && pytest video-ingestion/tests -v
```

---

## 3. Test Coverage by Milestone

- **Week 1 (Days 2–7):** Ingestion sources, YOLOv8 detector, ByteTrack tracker, spatial polygon containment, directional lines, and MJPEG streaming API (180+ tests).
- **Day 8 (ANPR):** Plate localization, preprocessing, OCR character distance, syntax rules, and consensus voting (35+ tests).
- **Day 9 (Watchlist):** Normalization, near-matcher look-alike costs, PostgreSQL repository contracts, DB failover, and Plan Tests 3 & 4 (65+ tests).
- **Day 10 (Identity & Re-ID):** Face quality gating, SFace embeddings, cosine matching, consent gating, and ColorLayout Re-ID retrieval (75+ tests).
- **Day 11 (Behaviour Rules):** Declarative rule schemas, condition evaluators, episode suppression, simulated clock, and Plan Tests 1, 2, 5, 6 (85+ tests).
- **Day 12 (Threat Scoring):** Scoring config validation, pure scoring arithmetic, decaying sliding window, plate-based entity merging, escalation alerting, Plan Scenarios 1 & 2 on real engines, evidence snapshots, and tooling (60+ tests).
- **Total:** **501 tests** passing with 100% green status.
