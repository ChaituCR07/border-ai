# Platform Documentation (`docs`)

The `docs/` directory contains engineering specifications, architectural diagrams, benchmark records, operational manuals, and Architecture Decision Records (ADRs) guiding the development and operation of the Border AI platform.

---

## 1. Directory Structure

```text
docs/
├── architecture.md            # Comprehensive multi-service system architecture & data flow (Sections 1–11)
├── threat_scoring.md          # Multi-factor threat scoring engine guide, formulas, & alert semantics
├── rules_engine.md            # Configurable behaviour rules engine specification (rules R001–R005)
├── watchlist.md               # PostgreSQL 16 watchlist architecture, near matching, & resilience
├── identity.md                # Facial biometric recognition and person appearance Re-ID guide
├── privacy.md                 # Biometrics governance, consent gating, and data retention policy
├── api.md                     # REST API specification and structured event schemas (including THREAT_ALERT)
├── testing.md                 # Testing strategy, pytest markers, and test mapping (Days 2–12)
├── known_issues.md            # Comprehensive known issues register (K1–K23) and mitigations
├── benchmarks.md              # Performance metrics (FPS, inference latencies, worker throughput)
├── ground_truth/              # Ground truth verification JSON definitions for evaluation clips
│   ├── anpr_vehicles.json
│   ├── anpr_vehicle_track.json
│   ├── behaviour_person_walking.json
│   └── threat_person_walking.json
├── images/                    # Architectural diagrams, workflow flowcharts, and visual assets
└── decisions/                 # Architecture Decision Records (ADRs)
    ├── 0001-local-dev-approach.md       # ADR 0001: Local host vs containerization approach
    ├── 0002-timestamp-convention.md     # ADR 0002: UTC epoch timestamp convention
    ├── 0007-anpr-design.md              # ADR 0007: PaddleOCR and consensus voting design
    ├── 0008-watchlist-design.md         # ADR 0008: PostgreSQL watchlist dual-backend and near matcher
    ├── 0009-identity-prototype.md       # ADR 0009: YuNet, SFace, and appearance Re-ID prototype
    ├── 0010-behaviour-engine.md         # ADR 0010: Declarative behaviour rules architecture
    └── 0011-threat-scoring.md           # ADR 0011: Composite threat scoring and escalation semantics
```

---

## 2. Core Documentation Index

### Architectural & System Guides
- **[`architecture.md`](./architecture.md):** Complete end-to-end system design spanning video ingestion, YOLOv8 detection, ByteTrack tracking, spatial geometry, ANPR, watchlist matching, facial biometrics, behaviour rules, and composite threat scoring.
- **[`threat_scoring.md`](./threat_scoring.md):** Formal specification of the threat scoring mathematical model: weights table, sliding time window (`window_s: 600`), plate-based track merging, exclusion rules, multi-suspicious bonuses, and escalation-only alerting.
- **[`rules_engine.md`](./rules_engine.md):** Declarative behaviour rules manual: schema specification, spatial/temporal/classification condition evaluators, and episode state machines.
- **[`watchlist.md`](./watchlist.md):** PostgreSQL 16 watchlist architecture, OCR-aware look-alike near matching algorithms, and automated in-memory snapshot resilience.
- **[`identity.md`](./identity.md):** YuNet face detection quality gate, SFace 128-d cosine similarity matching, and ColorLayout appearance Re-ID.
- **[`api.md`](./api.md):** REST endpoints (`/health`, `/model/info`, `/detect`) and complete event contracts (`ZONE_VIOLATION`, `WATCHLIST_MATCH`, `THREAT_ALERT`, etc.) mapped to database schemas.

### Governance, Privacy, & Quality
- **[`privacy.md`](./privacy.md):** Ethical biometrics governance, default-off security guarantees, mandatory consent-flagging for enrollments, and zero image persistence policy.
- **[`testing.md`](./testing.md):** Testing methodology covering **501 automated tests** across unit, dual-backend contract, database migration, pipeline integration, and plan scenario acceptance suites.
- **[`known_issues.md`](./known_issues.md):** Active operational tracking register covering edge cases (tracker ID switches, camera angle limits, async event arrival).
- **[`benchmarks.md`](./benchmarks.md):** Hardware benchmarking logs across CPU, Apple Silicon MPS, and NVIDIA GPU environments.
