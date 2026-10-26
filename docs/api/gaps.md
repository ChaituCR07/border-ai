# API & Pipeline Gap Tracking (Day 16 Frontend Integration)

This document tracks capabilities or data shapes desired by the React Command Dashboard that are not natively provided by the Day 15 REST API or Day 7 video streamer, along with the approved client-side mitigations or future roadmap items.

---

| Item | Frontend Need | Current API / Pipeline Reality | Approved Mitigation / Status |
|---|---|---|---|
| **G1: Camera Still JPEG Endpoint** | Sidebar thumbnails need occasional still image updates without holding a continuous HTTP stream open forever. | Day 7 MJPEG streaming server only exposes continuous `multipart/x-mixed-replace` streams at `/cam/{id}.mjpg`. | **Mitigation (ADR 0018):** Only open streams for currently mounted/visible tiles (max 4). Closed on tab hidden or unmount. Optional Python endpoint `GET /cam/{id}/latest.jpg` proposed for Day 17. |
| **G2: Real-time Camera Heartbeat** | Status dots (LIVE, CONNECTING, OFFLINE) on inactive cameras. | No persistent camera health ping or ping telemetry in DB yet. | **Mitigation:** Derive liveness from active stream `load`/`error` events for visible cameras, and `last_event_at` timestamp from `/api/analytics/cameras` for background cameras. Formal camera ping telemetry scheduled for Week 4. |
| **G3: Camera Name on Alert Cards** | Alerts list needs human-readable camera name (e.g. "North Gate Approach"). | `/api/alerts` returns `camera_id` from relation. | **Mitigation:** Client-side join using cached TanStack Query `cameras` list. Zero additional HTTP overhead. |
| **G4: Unacknowledged Alert Count** | Summary badges need instant open alert totals. | No dedicated `/api/alerts/count` endpoint. | **Mitigation:** TanStack Query reads `open_alerts_by_priority` from `/api/analytics/threats` (which accurately counts OPEN/NEW alerts). |
| **G5: WebSocket Event Stream** | Push alerts without polling. | Day 15 API uses HTTP REST polling only. | **Seam Designed:** `useOpenAlerts` hook defines `LiveAlerts` interface with `transport: 'polling' \| 'websocket'`. Day 17 swaps transport to WebSocket seamlessly. |
