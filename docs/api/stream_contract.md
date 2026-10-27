# Stream Contract Audit — `surveillance.alerts`

## 1. Stream Entry Schema
The AI Engine publishes events with `type: "THREAT_ALERT"` simultaneously to `surveillance.events` and `surveillance.alerts` using Redis Streams (`XADD`).

Each stream entry consists of flat key-value pairs according to the version 1 envelope:

| Field | Type | Description |
|---|---|---|
| `v` | string (`"1"`) | Schema envelope version |
| `event_id` | string (UUID) | Unique identifier of the triggering surveillance event |
| `type` | string | Event classification, e.g. `"THREAT_ALERT"` |
| `camera` | string | Camera identifier (e.g. `"CAM-01"`) |
| `ts` | string | Event epoch timestamp in milliseconds |
| `severity` | string | Priority rating (`"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, `"LOW"`) |
| `run_id` | string | Active pipeline execution run ID |
| `data` | string (JSON) | Complete serialized event dictionary |

## 2. Payload Structure (`data` JSON Object)
The `data` field contains:
```json
{
  "schema": 1,
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "type": "THREAT_ALERT",
  "camera": "CAM-03",
  "camera_id": "CAM-03",
  "track_id": 42,
  "timestamp": "2026-10-27T12:00:00.000000Z",
  "severity": "CRITICAL",
  "threat_score": 92,
  "plate": "KA01AB1234",
  "details": {
    "alert_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "priority": "CRITICAL",
    "threat_score": 92,
    "entity": "KA01AB1234",
    "summary": "Restricted Zone Entry",
    "event_type": "RESTRICTED_ZONE_ENTRY",
    "snapshot_path": "CAM-03/snapshot_123.jpg",
    "plate": "KA01AB1234"
  }
}
```

## 3. Key Contract Properties
1. **Stable `alert_id`:** The AI Engine behaviour and threat scoring engines generate a unique UUID `alert_id` placed into `details.alert_id`. The Postgres sink uses this as the primary key of the `alerts` row (`ON CONFLICT (alert_id) DO NOTHING`).
2. **Stream Retention:** Stream retention is bounded via `XTRIM MAXLEN ~ 10000` on `surveillance.alerts`.
3. **Sink Latency:** PostgreSQL consumer group commits transactions within 50–200 ms under normal load. The WebSocket gateway hydrator retries against Postgres at `[0, 50, 100, 200, 400, 800, 1500] ms` before falling back to `persisted: false`.
