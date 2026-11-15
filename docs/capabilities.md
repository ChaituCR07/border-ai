# Border-AI Platform Capabilities Matrix (Claims vs. Evidence)

This document establishes the authoritative capability mapping for the Border-AI Video Intelligence Platform. Every capability described across the README, marketing briefs, and technical documentation is grounded in specific source implementations and verified test evidence.

---

## 1. Authoritative Capability Status Vocabulary
- **`Implemented`:** Fully operational in production code, integrated into the composed stack, covered by automated test suites, and benchmarked.
- **`Prototype`:** Functional implementation available in the codebase; verified on sample fixtures, but explicitly designated as preview/off-by-default or consent-gated.
- **`Partial`:** Implemented for specific standard protocols or formats; broader integrations designated for future milestones.
- **`Not implemented`:** Explicitly out-of-scope for the `v1.0.0` milestone; documented in `docs/LIMITATIONS.md` and roadmap.

---

## 2. Capability Evidence Matrix

| Capability Area | Planned Feature | Implementation Status | Where Implemented | Empirical Evidence / Test Report | Architectural & Operational Notes |
|---|---|:---:|---|---|---|
| **Video Ingestion** | RTSP / IP Camera Ingestion | **Implemented** | `engine/ingestion/` | Day 21 `rtsp_live` scenario test, camera heartbeats | Thread-per-camera ingestion with bounded frame queues and auto-reconnect. |
| **Video Ingestion** | **ONVIF** Automated Discovery & PTZ | **Not implemented** | *None* | Documented in `docs/LIMITATIONS.md` | RTSP URLs are configured manually. ONVIF-conformant cameras exposing RTSP streams function cleanly. PTZ presets are deferred. |
| **Detection** | Real-Time Object Detection | **Implemented** | `engine/detector/yolo.py` | [`docs/model_eval/detection.md`](model_eval/detection.md) (`run-20261108-cctv-det`) | YOLOv8s deployed operating point achieves **86.4% mAP@50** on Border CCTV Mini; 8.0ms p50 latency. |
| **Tracking** | Multi-Object Tracking | **Implemented** | `engine/tracker/bytetrack.py` | [`docs/model_eval/tracking.md`](model_eval/tracking.md) (`run-20261108-mot17-track`) | ByteTrack Kalman tracker achieves **64.6% HOTA**, **71.4% MOTA**, and 92.2% track continuity on static CCTV splits. |
| **Spatial Analytics** | Restricted Zones & Tripwires | **Implemented** | `engine/spatial/` | `tests/test_spatial_engine.py`, Day 25 logic tests | Foot-point ground contact coordinates (ADR 0005) prevent false alerts from torso pitch. |
| **ANPR Engine** | Plate Localization & Character OCR | **Implemented** | `engine/anpr/` | [`docs/model_eval/anpr.md`](model_eval/anpr.md) (`run-20261109-anpr-eval`) | PaddleOCR PP-OCRv6 with 5-frame consensus achieves **98.4% plate accuracy** and 1.2% character error rate. |
| **Watchlist Intelligence**| Vehicle Watchlist Verification | **Implemented** | `backend/src/modules/watchlist/` | [`docs/testing/false_positive_report.md`](testing/false_positive_report.md) (`run:wl-20261112-01`) | **0.0 false matches** / 1,000 reads on 100-plate list under look-alike substitution cost matrix. Memory snapshot fallback on DB drop. |
| **Biometric Identity** | Facial Recognition & Cross-Cam Re-ID | **Prototype** | `engine/identity/` | [`docs/model_eval/model_cards/face_reid_prototype.md`](model_eval/model_cards/face_reid_prototype.md) | **Consent-gated prototype**, disabled by default. 128-d L2 embeddings; no search-by-image; matches emitted as investigative leads. |
| **Behaviour Rules** | Configurable Behaviour Rules | **Implemented** | `engine/rules/` | Day 11 unit tests, Day 25 logic tier validation | Evaluates declarative JSON rules (R001–R005) combining spatial, temporal, classification, and OCR states. |
| **Threat Scoring** | Composite Threat Scoring (0–100) | **Implemented** | `engine/threat/` | Scenarios S1 (Score 60) and S2 (Score 80) tests | 10-minute linear decaying sliding window with smart exclusion masks preventing duplicate points. |
| **Event Streaming** | Redis Streams Pipeline | **Implemented** | `engine/streaming/`, `backend/src/eventbus/` | Day 21 event reconciliation harness (`check_reconcile.py`) | High-throughput `surveillance.events` and `surveillance.alerts` streams with consumer groups and zero telemetry loss. |
| **Cross-Camera** | Topology Journey Correlation | **Implemented** | `backend/src/modules/correlation/` | Day 19 correlation tests, Scenario S3 validation | Reconstructs vehicle timelines across cameras with travel-time plausibility and impossible-speed anomaly detection. |
| **User Interface** | Live Command Center | **Implemented** | `frontend/src/` | Day 16 e2e suite, Playwright screenshot test | React 19 + TypeScript dashboard featuring 2×2 live MJPEG grid, alert cards, and real-time audio chimes. |
| **User Interface** | Forensic Investigation Workbench | **Implemented** | `frontend/src/pages/Investigation/` | Day 18 investigation tests | Keyset cursor pagination, look-alike plate search, timeline reconstruction, and CSV export. |
| **Notifications** | Transactional Email Notifications | **Implemented** | `backend/src/modules/notifications/` | Day 20 outbox tests, Mailpit integration drills | Anti-join transactional outbox polling (ADR 0029) guaranteeing at-least-once SMTP dispatch with inline snapshot evidence. |
| **Security & RBAC** | Least-Privilege Security & Audit | **Implemented** | `backend/src/security/` | 30/30 ASVS 4.0 controls passed (`backend/tests/security/`) | Argon2id password hashing, rotating refresh cookies, Ed25519 JWTs, deny-by-default RBAC, and SHA-256 hash-chained audit log. |
| **Security & RBAC** | Multi-Factor Authentication (MFA/SSO) | **Not implemented** | *None* | Documented in `docs/LIMITATIONS.md` | Single-tenant local RBAC implemented. OIDC / SAML SSO and TOTP MFA are scheduled for v1.1 roadmap. |
| **Deployment** | Whole-Platform Containerization | **Implemented** | `docker-compose.yml`, `Makefile` | [`docs/deployment/resilience_results.md`](deployment/resilience_results.md) | Single-command launch via `make quickstart`. 10 services, 3 segregated internal networks, 0 exposed internal ports. |
| **Deployment** | Kubernetes / Helm Orchestration | **Not implemented** | *None* | Documented in `docs/LIMITATIONS.md` | Single-host Docker Compose deployment. Multi-node Kubernetes orchestration explicitly deferred to post-v1. |

---

## 3. Compliance and Marketing Rule

In accordance with ADR 0053 and project guidelines:
1. No documentation, presentation, or portfolio material may claim **`Implemented`** status for capabilities marked as **`Prototype`** or **`Not implemented`**.
2. Face recognition and cross-camera Re-ID must always be qualified as a **consent-gated prototype**.
3. Camera ingestion must be described as **RTSP / IP-camera streams**, explicitly clarifying that automated ONVIF discovery is deferred.
