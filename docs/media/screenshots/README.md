# Border-AI Interface Screenshot Gallery

This gallery showcases the core user interfaces of the Border-AI Video Intelligence Platform running in production mode (`v1.0.0`). All screenshots are captured at **1920×1080** in dark mode with synthetic demo data and zero real personally identifiable information.

---

## 1. Live Operator Monitoring & Triage

| Screenshot Reference | View Name | Description |
|---|---|---|
| `01-login.png` | **Operator Login** | Clean authentication screen enforcing Argon2id password security and rotating refresh cookies. |
| `02-command-center-grid.png` | **Live Command Center** | Real-time 2×2 multi-camera MJPEG video grid with active bounding boxes and operational status indicators. |
| `03-critical-alert-toast.png` | **Critical Threat Toast** | Sub-50ms WebSocket alert toast triggered on watchlisted vehicle detection. |
| `04-alert-drawer-factor-checklist.png` | **Explainable Factor Drawer** | Inspection drawer displaying the pre-annotation evidence JPEG and mathematical factor breakdown checklist. |
| `05-scenario-1-card.png` | **Scenario 1 Alert Card** | Intrusion alert: Zone Entry (+30) + Tripwire (+20) + Night Clock (+10) = Score 60 (HIGH). |

---

## 2. Forensic Investigation & Administration

| Screenshot Reference | View Name | Description |
|---|---|---|
| `06-investigation-results.png` | **Forensic Investigation** | Historical sighting search featuring OCR look-alike phonetic matching and faceted filters. |
| `07-cross-camera-journey-view.png` | **Vehicle Journey Map** | Topological timeline tracing a vehicle across CAM-01 $\to$ CAM-02 $\to$ CAM-04 with travel-time plausibility. |
| `08-mailpit-email-notification.png` | **Transactional Email** | Incident email dispatch with inline snapshot evidence and direct deep links. |
| `09-system-health-status.png` | **Component Health Telemetry** | Real-time status of PostgreSQL, Redis Streams, AI Engine, and RTSP ingestion. |
| `10-admin-audit-log.png` | **Cryptographic Audit Trail** | Tamper-evident administrative audit log verified via SHA-256 hash chaining. |

---

## 3. Automation & Privacy Verification
Screenshots are generated automatically via Playwright (`npm run screenshots` or `ts-node scripts/media/screenshots.ts`) and verified for privacy compliance in `docs/media/PRIVACY_REVIEW.md`.
