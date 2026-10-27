# WebSocket Gateway Protocol Specification (v1)

**Endpoint:** `GET /api/ws`  
**Protocol:** WebSocket (`ws://` / `wss://`)  
**Package:** `@border-ai/protocol`  

---

## 1. Overview and Core Invariants

The Border-AI WebSocket Gateway provides real-time notification of perimeter security alerts.

1. **Ephemeral Notification, PostgreSQL Truth:**
   - Real-time messages are delivered **at-most-once**.
   - If a connection drops, a message is dropped, or a sequence gap is detected, the client performs a **REST resynchronization** (`GET /api/alerts?status=OPEN`).
2. **One DTO:**
   - The WebSocket alert view schema is identical to the REST alert view schema (`AlertView`), with an additional `persisted: boolean` flag indicating whether the database sink has committed the row.
3. **Monotonic Sequences & Epochs:**
   - Every state-changing message (`alert.created`, `alert.updated`, `resync_required`) increments a server sequence counter (`seq`).
   - `server_epoch` uniquely identifies the server process lifetime. If `server_epoch` changes on reconnect, the client must trigger a full resynchronization.
4. **Heartbeat & Gap Detection:**
   - The server broadcasts an application-level `{ v: 1, type: 'heartbeat', seq: N, server_time: '...' }` every 15 seconds.
   - If an idle client receives a heartbeat with `heartbeat.seq > client.last_seq`, the client immediately knows it missed messages and initiates a REST resync.

---

## 2. Connection Handshake & Security

### 2.1 Origin Allowlist
Upgrade requests are validated against the CORS allowed origins before completing the HTTP-to-WebSocket upgrade. Requests with missing or disallowed origins receive `403 Forbidden`.

### 2.2 Inbound Message Caps
- Maximum client frame payload: `1024 bytes`.
- Inbound rate limit: at most 20 messages per 10 seconds. Exceeding this closes the socket with `1008` (Policy Violation).

### 2.3 Slow Consumer Protection
- Per-client buffer cap: `1 MB` (`bufferedAmount > 1_048_576`).
- If a slow client exceeds this limit, the gateway closes the connection with code `1013` (Try Again Later) to protect server memory.

---

## 3. Server-to-Client Messages

All messages are JSON objects containing `v: 1`, `type: string`, and `seq: number`.

### 3.1 `hello`
Sent immediately upon successful connection establishment.
```json
{
  "v": 1,
  "type": "hello",
  "server_epoch": "8e3c54aa-1fb2-47c1-bf1a-351dd8c4e402",
  "seq": 482,
  "server_time": "2026-10-27T16:00:00.000000Z"
}
```

### 3.2 `heartbeat`
Broadcast every 15 seconds. Does not increment `seq`.
```json
{
  "v": 1,
  "type": "heartbeat",
  "seq": 482,
  "server_time": "2026-10-27T16:00:15.000000Z"
}
```

### 3.3 `alert.created`
Broadcast when a new perimeter alert is detected. Increments `seq`.
```json
{
  "v": 1,
  "type": "alert.created",
  "seq": 483,
  "data": {
    "alert": {
      "alert_id": "c71a396e-5da7-4e94-9b37-251f2a3260c1",
      "event_id": "0192e2b3-6c8a-7e1b-bf3d-246e4912ab01",
      "priority": "CRITICAL",
      "status": "OPEN",
      "acknowledged_by": null,
      "acknowledged_at": null,
      "created_at": "2026-10-27T16:00:20.123456Z",
      "persisted": true,
      "event": {
        "camera_id": "CAM-03",
        "event_type": "RESTRICTED_ZONE_ENTRY",
        "threat_score": 92,
        "plate": "KA01AB1234",
        "timestamp": "2026-10-27T16:00:19.890123Z",
        "snapshot_url": "/api/snapshots/0192e2b3-6c8a-7e1b-bf3d-246e4912ab01.jpg",
        "snapshot_available": true
      }
    }
  }
}
```

### 3.4 `alert.updated`
Broadcast when an alert state changes (e.g. operator acknowledgment). Increments `seq`.
```json
{
  "v": 1,
  "type": "alert.updated",
  "seq": 484,
  "data": {
    "alert": {
      "alert_id": "c71a396e-5da7-4e94-9b37-251f2a3260c1",
      "event_id": "0192e2b3-6c8a-7e1b-bf3d-246e4912ab01",
      "priority": "CRITICAL",
      "status": "ACKNOWLEDGED",
      "acknowledged_by": "operator-01",
      "acknowledged_at": "2026-10-27T16:00:28.456789Z",
      "created_at": "2026-10-27T16:00:20.123456Z",
      "persisted": true,
      "event": {
        "camera_id": "CAM-03",
        "event_type": "RESTRICTED_ZONE_ENTRY",
        "threat_score": 92,
        "plate": "KA01AB1234",
        "timestamp": "2026-10-27T16:00:19.890123Z",
        "snapshot_url": "/api/snapshots/0192e2b3-6c8a-7e1b-bf3d-246e4912ab01.jpg",
        "snapshot_available": true
      }
    }
  }
}
```

### 3.5 `resync_required`
Sent when the gateway experienced an internal recovery or stream reconnection. Increments `seq`.
```json
{
  "v": 1,
  "type": "resync_required",
  "seq": 485,
  "reason": "gateway_stream_reconnected"
}
```

---

## 4. Client-to-Server Messages

### 4.1 `ping`
```json
{
  "v": 1,
  "type": "ping"
}
```
The server responds immediately with a `heartbeat` message.

---

## 5. Close Codes

| Code | Reason | Client Action |
|---|---|---|
| `1000` | Normal closure (e.g. client navigation or cleanup) | Do not reconnect unless requested |
| `1001` | Going away (e.g. server restart) | Reconnect with exponential backoff |
| `1008` | Policy violation (e.g. rate limit, invalid frame) | Reconnect with backoff; log error |
| `1009` | Message too big (> 1024 bytes) | Fix client message size |
| `1013` | Try again later (server full or slow consumer) | Backoff and retry (jittered) |
