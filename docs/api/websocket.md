# Border-AI WebSocket Real-Time Alert Streaming Contract (Day 17 Hand-off)

## 1. Overview
On Day 17, live alert delivery transitions from REST polling (`GET /api/alerts?status=OPEN`) to a bidirectional WebSocket transport (`/ws/alerts`).
This document specifies the message protocol, reconnection sequence recovery, and synchronization hand-off between backend Redis alert streams and the frontend `useOpenAlerts` seam.

---

## 2. Handshake and Connection Protocol

### 2.1 Endpoint
```text
ws://localhost:4000/ws/alerts
wss://<production_domain>/ws/alerts
```

### 2.2 Server Hello Message
Immediately upon connection establishment, the server transmits a hello message containing the current microsecond server timestamp:
```json
{
  "v": 1,
  "type": "hello",
  "server_time": "2026-10-26T20:00:00.000000Z",
  "session_id": "ws-sess-01j9b2k3e4r5t6y7u8i9o0p"
}
```

---

## 3. Real-Time Event Frames

Each notification frame increments an monotonically increasing per-session sequence counter `seq`:

### 3.1 Alert Created (`alert.created`)
Broadcast when an alert is created by the Threat Scoring Engine and inserted into the Postgres/Redis stream `surveillance.alerts`:
```json
{
  "v": 1,
  "type": "alert.created",
  "seq": 10234,
  "data": {
    "alert_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "event_id": "11111111-1111-1111-1111-111111111111",
    "priority": "CRITICAL",
    "status": "OPEN",
    "acknowledged_by": null,
    "acknowledged_at": null,
    "created_at": "2026-10-26T20:01:15.123456Z",
    "event": {
      "camera_id": "CAM-01",
      "event_type": "RESTRICTED_ZONE_ENTRY",
      "threat_score": 95,
      "plate": "KA01AB1234",
      "snapshot_url": "/api/snapshots/CAM-01/snap1.jpg"
    }
  }
}
```

### 3.2 Alert Updated (`alert.updated`)
Broadcast when an operator acknowledges an alert or when an alert resolves:
```json
{
  "v": 1,
  "type": "alert.updated",
  "seq": 10235,
  "data": {
    "alert_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "priority": "CRITICAL",
    "status": "ACKNOWLEDGED",
    "acknowledged_by": "operator-chaitanya",
    "acknowledged_at": "2026-10-26T20:02:00.000000Z"
  }
}
```

---

## 4. Gap Detection & REST Catch-Up

1. **Sequence Discontinuity:**
   If a client receives a frame where `seq > last_seen_seq + 1`, a network gap is inferred.
2. **REST Catch-Up:**
   The client immediately executes a REST catch-up query:
   ```http
   GET /api/alerts?status=OPEN&from=<last_seen_created_at>&limit=50
   ```
3. **Reconnection Recovery:**
   Upon reconnecting after a network dropout, the client queries REST for open alerts and resumes sequence tracking from the new connection's `hello` event.

---

## 5. Client Heartbeat Ping/Pong
- Client transmits `{"type": "ping"}` every 20 seconds.
- Server responds with `{"type": "pong"}`.
- Connection is marked degraded if no pong is received within 10 seconds.
