# Border-AI 28-Day Architectural Retrospective

**Milestone:** v1.0.0 Production Release  
**Date:** 2026-11-15  
**Author:** Chaitanya Medam (ChaituCR07)  

---

## 1. Executive Summary

Over 28 consecutive days of intensive engineering, the Border-AI platform evolved from an initial concept into an enterprise-grade, containerized AI video intelligence platform. Across more than 450 commits, 55 Architecture Decision Records (ADRs), and 280+ automated tests, the system delivers real-time detection, tracking, ANPR, rule evaluation, threat scoring, and forensic investigation.

This retrospective captures what worked exceptionally well, what technical trade-offs were made, and what we would approach differently in future platform iterations.

---

## 2. What Worked Exceptionally Well

1. **The Architecture Decision Record (ADR) Habit:**
   - Documenting architectural trade-offs in `docs/decisions/` *before* implementation was the single highest-leverage engineering practice. It prevented scope creep, clarified boundary contracts between Python and TypeScript, and created an auditable portfolio log that explains the *why* behind every technical choice.
2. **Foot-Point Ground Contact Geometry (ADR 0005):**
   - Rejecting center-bounding-box spatial intersection in favor of the bottom-center foot coordinate eliminated false perimeter intrusion alarms caused by pedestrian torso sway, camera pitch angles, or shadow extensions.
3. **Decoupled Polyglot Architecture with Strict Data Ownership (ADR 0014):**
   - Granting the Python AI Engine write ownership solely over detection events and sightings while granting the Node.js Fastify API write ownership over alert acknowledgements and audit trails eliminated database deadlocks and distributed locking complexity.
4. **Local Append-Only Journaling (ADR 0014):**
   - The engine's local SQLite/file journal buffer prevented a single telemetry drop during simulated PostgreSQL or Redis container crashes (resilience scenarios R1–R3), flushing cleanly upon database recovery.
5. **Keyset Cursor Pagination (ADR 0015):**
   - Standard offset-based pagination (`OFFSET N LIMIT M`) fails in high-frequency video surveillance. Implementing deterministic keyset pagination on `(timestamp DESC, event_id DESC)` enabled smooth, drift-free forensic investigation scrolling.
6. **Empirical Benchmarking with Confidence Intervals (ADR 0040):**
   - Auditing every model accuracy and latency metric with 1,000-resample bootstrap 95% confidence intervals and run tags established uncompromising credibility and prevented ungrounded marketing claims.

---

## 3. What We Would Do Differently

1. **Earlier Full Containerization:**
   - Full Docker Compose containerization was executed in Week 4 (Day 27). While this allowed rapid local development in Weeks 1–3, postponing multi-container networking created late integration hurdles around non-root volume permissions (UID 10001 vs 10002) and Linux vs macOS MPS GPU passthrough. In future projects, a minimal Docker Compose stack should be introduced in Week 1.
2. **Standardized Model Weight Hashing from Day 1:**
   - Model weights (YOLO, PaddleOCR) were initially downloaded via runtime scripts. Transitioning to an immutable SHA-256 lockfile manifest (`configs/models.lock.json`) on Day 27 proved essential for supply chain security; this should have been the baseline from inception.
3. **Hardware-Accelerated Video Decoding:**
   - CPU-based FFmpeg RTSP decoding consumed a significant portion of the compute budget during N=8 camera scaling. Integrating hardware-accelerated video decoding (NVIDIA NVDEC or Intel VAAPI) inside containers would substantially reduce CPU overhead.

---

## 4. Maintenance & Platform Evolution (Roadmap to v1.1)

- **Automated Dependency Auditing:** Weekly Dependabot and Trivy container vulnerability scanning.
- **ONVIF Discovery & PTZ Tracking:** Implementing automated camera discovery via WS-Discovery and automated PTZ zoom tracking on high-threat targets.
- **Enterprise Identity (SSO/MFA):** Adding OpenID Connect (OIDC) and SAML 2.0 integration for enterprise identity providers (Okta, Azure AD), alongside TOTP multi-factor authentication.
- **Multi-Instance Clustering:** Migrating from single-host Docker Compose to Kubernetes with horizontal pod autoscaling and distributed Redis pub/sub WebSocket synchronization.
