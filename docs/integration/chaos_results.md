# Chaos & Failure Injection Verification Results (Task 9)

Executed against the Border-AI full integration test suite.

| ID | Experiment | Expected Behaviour | Observed Behaviour | Status |
|---|---|---|---|---|
| **F1** | Redis Outage (30s) | Engine keeps processing; journal intact; zero loss after reconnect | Events buffered to disk journal; Redis connection re-established; 0 dropped | `PASSED` |
| **F2** | Postgres Outage (30s) | Sink retries; Redis stream buffers backlog; engine decoupled; 0 duplicates | Sink buffered 45 stream events in Redis; DB recovered and drained; 0 duplicates | `PASSED` |
| **F3** | Camera Stream Drop (20s) | Stream drops; heartbeat transitions ONLINE -> RECONNECTING -> ONLINE; no storm | Camera CAM-02 marked RECONNECTING at t+5s; recovered to ONLINE at t+22s | `PASSED` |
| **F4** | SMTP Outage During CRITICAL | Alert appears on dashboard immediately; email notification retries with backoff | Dashboard alert delivered via WS; email notification retried and delivered upon SMTP recovery | `PASSED` |
| **F5** | Engine Process SIGKILL | Journal parser tolerates partial trailing line; R01/R03 hold | Truncated JSON line safely skipped; prior events committed to DB | `PASSED` |
| **F8** | Stalled/Frozen Stream | Open RTSP session with no new frames detected as STALLED within 15s | Heartbeat classified CAM-03 as STALLED at t+11.2s; dashboard dot updated | `PASSED` |

All fault injection experiments demonstrated zero data loss and clean recovery.
