# Testing Strategy & Test Map

## 1. Testing Strategy

| Layer | What it proves | Dependencies | Pytest Marker | Execution Speed |
|---|---|---|---|---|
| **Unit** | Pure logic: normalization, distance, scoring, status rules, config | None | None | < 100 ms |
| **Repository Contract** | In-memory and PostgreSQL repositories behave **identically** | PostgreSQL for postgres parameter | `db` on postgres parameter | ~1-2 s |
| **Database** | Migrations, constraints, concurrency, partial indexes | PostgreSQL | `db` | ~1 s |
| **Service** | Worker flow, deduplication, cooldown, fallback, hits, flags | None (uses in-memory repo) | None | ~300 ms |
| **Integration** | Real pipeline (tracker, threads, rule engine, ANPR, watchlist) | Ultralytics / OpenCV | `integration` (+ `db`) | ~3-8 s |
| **Scenario / Acceptance**| Plan specifications: Test 3, Test 4, and Scenario 2 | None | None | ~100 ms |
| **Security / Privacy** | SQL injection protection, absence of sensitive names in events | None / PostgreSQL | None / `db` | ~100 ms |
| **Scale** | Lookup correctness and speed with 10,000 active entries | None | `slow` | ~4 s |

---

## 2. Test Commands

```bash
# Fast feedback loop (no database required, skips slow tests)
cd ai-engine && pytest -m "not db and not slow" -v

# Database tests only (requires running PostgreSQL container)
cd ai-engine && pytest -m db -v

# Full suite (database tests skip cleanly if PostgreSQL is offline)
cd ai-engine && pytest -v

# Full suite with coverage report
cd ai-engine && pytest -m "not slow" --cov=app --cov-report=term-missing

# Video ingestion tests
pytest video-ingestion/tests -v
```

---

## 3. Complete Project Test Map (Days 2 to 11)

| Day | Modules Protected | Key Test Files |
|---|---|---|
| 2 | Ingestion & Sources | `video-ingestion/tests/test_sources.py` |
| 3 | Detection & Utilities | `ai-engine/tests/test_detection_utils.py` |
| 4 | Detector & API Contracts | `ai-engine/tests/test_schemas.py`, `test_api.py`, `test_detector.py` |
| 5 | Multi-Camera Tracking | `ai-engine/tests/test_track_store.py`, `test_tracker.py`, `test_tracking_metrics_and_draw.py` |
| 6 | Spatial Rules & Geometries | `ai-engine/tests/test_geometry.py`, `test_rules_config.py`, `test_zone_engine.py`, `test_line_engine.py`, `test_rule_engine_and_overlays.py` |
| 7 | End-to-End Pipeline & Streaming | `ai-engine/tests/test_pipeline_plumbing.py`, `test_pipeline_integration.py`, `test_stream_api.py` |
| 8 | ANPR & Consensus Voting | `ai-engine/tests/test_plate_format.py`, `test_consensus.py`, `test_anpr_preprocess_and_locator.py`, `test_ocr_parsing.py`, `test_anpr_metrics.py`, `test_anpr_service.py`, `test_pipeline_anpr.py` |
| 9 | Watchlist & Resilience | `ai-engine/tests/test_watchlist_normalize.py`, `test_watchlist_matcher.py`, `test_watchlist_config_and_csv.py`, `test_watchlist_repo_contract.py`, `test_watchlist_db.py`, `test_watchlist_service.py`, `test_watchlist_scenarios.py`, `test_events_contract.py`, `test_pipeline_watchlist.py`, `test_watchlist_scale.py` |
| 10 | Identity & Person Re-ID | `ai-engine/tests/test_identity_core.py`, `test_identity_face_and_reid_embedder.py`, `test_identity_service.py`, `test_identity_enroll.py`, `test_identity_repo_extension.py`, `test_pipeline_identity.py` |
| 11 | Behaviour Rules & Scenarios | `ai-engine/tests/test_behaviour_config.py`, `test_behaviour_conditions.py`, `test_behaviour_engine.py`, `test_behaviour_scenarios.py`, `test_pipeline_behaviour.py`, `test_behaviour_tools.py` |
| 12 | Threat Scoring & Evidence Snapshots | `ai-engine/tests/threat_helpers.py`, `test_threat_config.py`, `test_threat_scoring_math.py`, `test_threat_scorer.py`, `test_threat_scenarios.py`, `test_pipeline_threat.py`, `test_threat_tools.py` |

---

## 4. Guiding Principles
- **No Hard Timing Assertions:** Tests do not assert strict wall-clock durations to avoid flakiness across differing CI environments.
- **Temporary Database Fixtures:** PostgreSQL tests dynamically create an ephemeral database (`borderai_test_<id>`) and drop it on teardown. The dev database is never polluted.
- **Zero Real PII:** All test datasets utilize strictly synthetic identifiers (`KA01AB1234`, `MH12XY4321`, `DL08CZ9999`).
