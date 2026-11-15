# Border-AI Architecture Decision Records (ADRs)

This directory logs the architectural, design, operational, and security decisions that govern the Border-AI Video Intelligence Platform across its 28-day lifecycle.

## Ten Architecture Decisions that Shaped Border-AI

1. **Foot-Point Ground Contact for Spatial Tripwires ([ADR 0005](0005-zone-tripwire-semantics-hysteresis.md)):** Anchoring spatial zone and line crossing checks to the bottom-center foot coordinate of bounding boxes eliminated false triggers caused by torso sway, camera angle pitch, and upper-body projections.
2. **Track-Level Aggregation & Summaries ([ADR 0013](0013-storage-tiering-and-track-level-aggregation.md)):** Persisting structured track life summaries instead of raw per-frame bounding boxes reduced relational storage volume by 99.5% while preserving forensic fidelity.
3. **Local Journal + Redis Streams + Idempotent Postgres ([ADR 0014](0014-polyglot-pipeline-data-ownership.md)):** A local append-only journal in the AI engine ensures zero telemetry loss during transient network partitions, flushing seamlessly via Redis Streams to idempotent PostgreSQL sinks upon recovery.
4. **WebSocket Notifications with REST Keyset Resync ([ADR 0020](0020-websocket-alert-protocol.md)):** Real-time alerting over WebSockets notifies operators within 50ms, while the database remains the immutable source of truth, backed by $O(1)$ cursor-paginated REST endpoints.
5. **Transactional Database Outbox for Notifications ([ADR 0029](0029-transactional-outbox-email-delivery.md)):** Anti-join transactional outbox polling guarantees reliable, at-least-once external SMTP email dispatch without distributed transaction overhead.
6. **Keyset Pagination with Microsecond Timestamps ([ADR 0015](0015-keyset-pagination-for-events.md)):** Stable `(timestamp DESC, event_id DESC)` cursor pagination guarantees zero row skipping or duplicate entries when navigating fast-moving real-time CCTV event streams.
7. **Phonetic & Look-Alike Watchlist Matrix ([ADR 0023](0023-ocr-lookalike-classes-and-levenshtein.md)):** Modeling character substitution costs (`B/8`, `O/0`, `1/I`, `S/5`) enables high-recall vehicle watchlist matching despite environmental camera blur and glare.
8. **Explainable Multi-Camera Topology Plausibility ([ADR 0026](0026-multi-camera-topology-correlation.md)):** Reconstructing vehicle journeys across cameras using configured transition bounds, speed plausibility, and anomaly penalties (impossible speed flag) surfaces reliable suspect timelines.
9. **Event Reconciliation as System Correctness Oracle ([ADR 0034](0034-e2e-event-reconciliation-harness.md)):** Automated reconciliation harnesses verify mathematical invariants between video truth, AI engine detections, streaming queues, and database records.
10. **Deny-by-Default RBAC & Secret Isolation ([ADR 0048](0048-least-privilege-rbac-and-security-hardening.md), [ADR 0050](0050-deployment-topology-networks-run-modes.md)):** Strict non-root execution, 3-tier internal network segmentation, zero plaintext secrets in images, and file-based runtime secrets prevent privilege escalation and lateral movement.

---

## Complete Architecture Decision Log

| ADR | Title | Status | Primary Decision / Architectural Impact |
|---|---|---|---|
| **0001** | [0001 - Local Development Architecture and Environment Strategy](0001-local-dev-approach.md) | `Accepted` | Core Infrastructure (PostgreSQL 16 & Redis 7)** will run inside lightweight Docker cont... |
| **0002** | [0002 - Timestamp Convention Across Pipeline and Cameras](0002-timestamp-convention.md) | `Accepted` | Wall-clock UTC epoch timestamp:** |
| **0003** | [0003 - 0003: Detection Configuration](0003-detection-config.md) | `Accepted` | We adopt the following standard production detection configuration: |
| **0004** | [0004 - 0004: Multi-Object Tracking Integration via ByteTrack](0004-tracking-integration.md) | `Accepted` | We adopt **ByteTrack** executed as a decoupled, downstream tracking stage immediately f... |
| **0005** | [0005 - 0005: Declarative Spatial Rule Engine & Event Generation](0005-rule-engine.md) | `Accepted` | We adopt a declarative, state-machine-driven spatial analytics engine decoupled from mo... |
| **0006** | [0006 - 0006. Pipeline Architecture and Stage Threading](0006-pipeline-architecture.md) | `Accepted` | 0006. Pipeline Architecture and Stage Threading |
| **0007** | [0007 - 0007. Automatic Number Plate Recognition (ANPR) Architecture and Consensus Engine](0007-anpr-design.md) | `Accepted` | 0007. Automatic Number Plate Recognition (ANPR) Architecture and Consensus Engine |
| **0008** | [0008 - Architecture Decision Record 0008: Watchlist System Design](0008-watchlist-design.md) | `Accepted` | Architecture Decision Record 0008: Watchlist System Design |
| **0009** | [0009 - Architecture Decision Record 0009: Face & Person Re-ID Prototype](0009-identity-prototype.md) | `Accepted` | Architecture Decision Record 0009: Face & Person Re-ID Prototype |
| **0010** | [0010 - 10. Behaviour Engine (Configurable Rules)](0010-behaviour-engine.md) | `Accepted` | 10. Behaviour Engine (Configurable Rules) |
| **0011** | [0011 - 0011. Threat Scoring Engine Architecture and Semantics](0011-threat-scoring.md) | `Accepted` | 0011. Threat Scoring Engine Architecture and Semantics |
| **0012** | [0012 - 0012. Event Bus Architecture, Delivery Guarantees, and Stream Semantics](0012-event-bus.md) | `Accepted` | 0012. Event Bus Architecture, Delivery Guarantees, and Stream Semantics |
| **0013** | [0013 - 0013. Core Database Schema, Entity Semantics, and Persistence Architecture](0013-core-database.md) | `Accepted` | 0013. Core Database Schema, Entity Semantics, and Persistence Architecture |
| **0014** | [0014 - ADR 0014 — Backend Stack, Framework Choice, and Data Ownership](0014-backend-stack-and-data-ownership.md) | `Accepted` | Technology Stack:** |
| **0015** | [0015 - ADR 0015 — Keyset Cursor Pagination and Microsecond Timestamp Precision](0015-pagination-and-timestamp-precision.md) | `Accepted` | Keyset (Cursor) Pagination:** |
| **0016** | [0016 - ADR 0016 — API Mutation Semantics, Idempotency, and Biometric Boundaries](0016-mutation-semantics.md) | `Accepted` | Atomic and Idempotent Alert Acknowledgement:** |
| **0017** | [0017 - ADR 0017 — Frontend Stack and Data Layer Architecture](0017-frontend-stack-and-data-layer.md) | `Accepted` | Core Framework & Build Tooling:** |
| **0018** | [0018 - ADR 0018 — Live Video Delivery Constraints and Connection Safety](0018-live-video-delivery-constraints.md) | `Accepted` | Hard Upper Bound on Active Streams:** |
| **0019** | [0019 - ADR 0019 — Operational UI Principles and Visual Ergonomics](0019-operational-ui-principles.md) | `Accepted` | Never Color Alone (Redundancy Principle):** |
| **0020** | [0020 - ADR 0020 — Real-Time WebSocket Gateway and Resynchronization Architecture](0020-websocket-gateway-design.md) | `Accepted` | ADR 0020 — Real-Time WebSocket Gateway and Resynchronization Architecture |
| **0021** | [0021 - ADR 0021 — Alert Notification Policy and Fatigue Mitigation](0021-alert-notification-policy.md) | `Accepted` | ADR 0021 — Alert Notification Policy and Fatigue Mitigation |
| **0022** | [0022 - ADR 0022 — WebSocket Security, Back-Pressure, and Connection Limits](0022-websocket-security-and-limits.md) | `Accepted` | ADR 0022 — WebSocket Security, Back-Pressure, and Connection Limits |
| **0023** | [0023 - ADR 0023 — Forensic Plate Normalization, Look-Alike Matching, and Time-of-Day Search Semantics](0023-plate-and-time-search-semantics.md) | `Accepted` | ADR 0023 — Forensic Plate Normalization, Look-Alike Matching, and Time-of-Day Search Se... |
| **0024** | [0024 - ADR 0024 — Forensic Search Privacy Guardrails, Role Gating, and Audit Logging](0024-investigation-privacy-roles-audit.md) | `Accepted` | ADR 0024 — Forensic Search Privacy Guardrails, Role Gating, and Audit Logging |
| **0025** | [0025 - ADR 0025 — Investigation UI Architecture, URL State, and Virtualized Rendering](0025-investigation-ui-state-and-rendering.md) | `Accepted` | ADR 0025 — Investigation UI Architecture, URL State, and Virtualized Rendering |
| **0026** | [0026 - ADR 0026 — Camera Topology Graph, Link Plausibility, and Explainable Confidence](0026-correlation-model-plausibility-confidence.md) | `Accepted` | ADR 0026 — Camera Topology Graph, Link Plausibility, and Explainable Confidence |
| **0027** | [0027 - ADR 0027 — Trips, Trajectories, Greedy Assignment, and Anomaly Taxonomy](0027-trips-trajectories-and-anomalies.md) | `Accepted` | ADR 0027 — Trips, Trajectories, Greedy Assignment, and Anomaly Taxonomy |
| **0028** | [0028 - ADR 0028 — Privacy Scopes, Sequence Search Governance, and Caching](0028-scope-and-privacy-of-correlation.md) | `Accepted` | ADR 0028 — Privacy Scopes, Sequence Search Governance, and Caching |
| **0029** | [0029 - ADR 0029 — Notification Architecture: Outbox Pattern, Advisory Lock, and Concurrent Workers](0029-notification-architecture-outbox.md) | `Accepted` | ADR 0029 — Notification Architecture: Outbox Pattern, Advisory Lock, and Concurrent Wor... |
| **0030** | [0030 - ADR 0030 — Notification Policy: Content Delivery, Rate Limiting, and Privacy Guardrails](0030-notification-policy-content-and-privacy.md) | `Accepted` | ADR 0030 — Notification Policy: Content Delivery, Rate Limiting, and Privacy Guardrails |
| **0031** | [0031 - ADR 0031 — Alert Lifecycle: Generation Invariants, Escalation Double-Safety, and Resolution](0031-alert-lifecycle-and-generation-guarantees.md) | `Accepted` | ADR 0031 — Alert Lifecycle: Generation Invariants, Escalation Double-Safety, and Resolu... |
| **0032** | [0032 - Integration Test Architecture — Replay Modes, Scenario Specs & Assertions](0032-integration-test-architecture.md) | `Accepted` | ### 1. Three Replay Modes |
| **0033** | [0033 - Engine Heartbeat & System Status Aggregation](0033-engine-heartbeat-and-system-status.md) | `Accepted` | ### 1. Redis Heartbeat with TTL Expiry |
| **0034** | [0034 - Reconciliation as the Correctness Oracle (Zero Loss Definition)](0034-reconciliation-as-correctness-oracle.md) | `Accepted` | ### 1. Invariants of "Zero Loss" |
| **0035** | [0035 - Evaluation Methodology, Reproducibility, Run Manifests, and Statistical Rigor](0035-evaluation-methodology-reproducibility-statistics.md) | `Accepted` | Run Manifest Schema & Provenance**: Every evaluation execution must produce an immutabl... |
| **0036** | [0036 - Detector Class Mapping, Benchmark Protocol, and Deployed Operating Points](0036-detector-class-mapping-protocol-and-operating-points.md) | `Accepted` | Explicit Class Mapping Schemas**: |
| **0037** | [0037 - Tracking Evaluation Protocol, MOT17 Sequence Partitioning, and Tuning Policy](0037-tracking-evaluation-protocol-and-tuning-policy.md) | `Accepted` | Protocol Separation**: |
| **0038** | [0038 - ANPR Evaluation Protocol, Stage Funnel, and Split Policy](0038-anpr-evaluation-protocol-and-stage-funnel.md) | `Accepted` | Three-Tier Evaluation Modes**: |
| **0039** | [0039 - Look-Alike Classes, Watchlist Matching, and Evidence-Driven Change Policy](0039-lookalike-classes-and-watchlist-matching-evidence-policy.md) | `Accepted` | Evidence-Driven Review Policy**: |
| **0040** | [0040 - Model Performance Reporting and Claims Policy](0040-model-performance-reporting-and-claims-policy.md) | `Accepted` | Tuple Requirement for Every Public Metric**: |
| **0041** | [0041 - Performance Measurement Methodology, Named Metrics, and Stability Criteria](0041-performance-measurement-methodology.md) | `Accepted` | Standardized Named Metrics**: |
| **0042** | [0042 - Overload Behavior, Graceful Degradation Order, and Rule-Correctness Floor](0042-overload-and-degradation-policy.md) | `Accepted` | Guiding Principle: Freshness Over Completeness**: |
| **0043** | [0043 - Capacity Sizing Guidelines, Mathematical Modeling, and Hardware Extrapolation Policy](0043-capacity-and-sizing-claims.md) | `Accepted` | Standard Measured Claim Form**: |
| **0044** | [0044 - 44. False-Positive Testing Methodology and Evidence Tiers](0044-false-positive-testing-methodology.md) | `Accepted` | 44. False-Positive Testing Methodology and Evidence Tiers |
| **0045** | [0045 - 45. False-Positive Confirmation, Suppression, and Sensitivity Guardrails](0045-confirmation-and-suppression-policy.md) | `Accepted` | 45. False-Positive Confirmation, Suppression, and Sensitivity Guardrails |
| **0046** | [0046 - 46. Alert-Fatigue Targets and False-Positive Reporting Policy](0046-alert-fatigue-targets-and-reporting.md) | `Accepted` | 46. Alert-Fatigue Targets and False-Positive Reporting Policy |
| **0047** | [0047 - 47. Authentication Design: EdDSA Access Tokens, Rotating Refresh Tokens, and Argon2id Hashing](0047-authentication-design.md) | `Accepted` | 47. Authentication Design: EdDSA Access Tokens, Rotating Refresh Tokens, and Argon2id H... |
| **0048** | [0048 - 48. Authorization: Permission Policy, Role Mappings, and Deny-by-Default Architecture](0048-authorization-permissions-and-deny-by-default.md) | `Accepted` | 48. Authorization: Permission Policy, Role Mappings, and Deny-by-Default Architecture |
| **0049** | [0049 - 49. Secrets Vault, Audit Integrity, and Least-Privilege Infrastructure](0049-secrets-vault-audit-integrity-and-least-privilege.md) | `Accepted` | 49. Secrets Vault, Audit Integrity, and Least-Privilege Infrastructure |
| **0050** | [0050 - Production Deployment Topology, Networks, and Run Modes](0050-deployment-topology-networks-run-modes.md) | `Accepted` | Service Architecture & Segmentation:** |
| **0051** | [0051 - Container Images, Supply Chain Integrity, and Model Distribution](0051-images-supply-chain-and-models.md) | `Accepted` | Multi-Stage Container Builds:** |
| **0052** | [0052 - Secrets Provisioning, Edge Proxy, TLS, and Operations](0052-secrets-tls-edge-and-operations.md) | `Accepted` | File-Based Secrets Provisioning (`*_FILE` Pattern):** |
| **0053** | [0053 - Documentation Governance — Single Sources of Truth](0053-documentation-governance-single-sources-of-truth.md) | `Accepted` | Single Sources of Truth Matrix:** |
| **0054** | [0054 - Open-Source Licensing, Third-Party Notices, and Responsible Use Policy](0054-licenses-third-party-notices-and-responsible-use.md) | `Accepted` | Platform Repository License:** |
| **0055** | [0055 - Demo and Media Publication Policy](0055-demo-and-media-policy.md) | `Accepted` | Synthetic and Controlled Media Only:** |
