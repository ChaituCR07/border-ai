# ADR 0022 — WebSocket Security, Back-Pressure, and Connection Limits

## Status
Accepted

## Context
Exposing long-lived bidirectional WebSocket endpoints (`/api/ws`) introduces denial-of-service risks, slow-consumer memory bloat, cross-site WebSocket hijacking (CSWSH), and credential leakage. Guardrails must be enforced at the gateway boundary.

## Decisions

1. **Origin Verification on Handshake (CSWSH Protection):**
   - The WebSocket upgrade request checks the HTTP `Origin` header against the application's CORS allowlist during `preValidation`.
   - Unauthorized origins are rejected immediately with HTTP 403 Forbidden before upgrading the TCP socket.

2. **Authentication Seam and Future Ticket Flow:**
   - Web browsers cannot attach custom HTTP headers to standard `WebSocket()` handshakes.
   - Long-lived JWT tokens must **never** be passed in query strings (which leak into access logs and browser histories).
   - Day 17 implements an extensible authentication seam (`authenticateWs(req)`). Day 26 will issue short-lived, single-use tickets via `POST /api/ws-ticket` passed as `?ticket=<single_use_token>` and discarded upon connection.

3. **Inbound Message Restrictions and Flood Protection:**
   - The server only accepts minimal client ping messages (`{ v: 1, type: 'ping' }`).
   - Maximum client message payload is capped at 1024 bytes (`maxPayload: 1024`).
   - Client messages are validated against the Zod `ClientMessage` schema; invalid JSON or unparseable messages are safely ignored without crashing the server.
   - Rate limiting: more than 20 messages per 10-second window from a client triggers immediate socket termination with code `1008` (Policy Violation).

4. **Slow Consumer Protection and Server Memory Safeguards:**
   - Per-client buffered amount is capped at 1 MB (`bufferedAmount > 1_048_576`).
   - If a lagging or intentionally slow client exceeds this threshold during broadcast, the server immediately closes the socket with code `1013` (Try Again Later).
   - This prevents slow readers from ballooning Node.js process memory (`RSS`).

5. **Connection Capacity:**
   - Default connection limit: `WS_MAX_CLIENTS = 200` per gateway instance.
   - Additional connection attempts beyond the ceiling are rejected with code `1013` ("server full").

6. **Dual Heartbeat Architecture:**
   - **TCP / Protocol Level:** Server issues periodic `ping` frames every 15 seconds. Sockets that fail to respond with `pong` before the next tick are terminated.
   - **Application Level:** Server broadcasts `{ v: 1, type: 'heartbeat', seq: N, server_time: '...' }` every 15 seconds. Browsers can observe this to detect silent connection drops (NAT timeout, laptop sleep) via a 45-second watchdog timer, and proxies (Nginx default 60s idle timeout) are kept alive.

7. **Zero Biometric / PII Leakage:**
   - In accordance with ADR 0009, the WebSocket gateway never includes facial embeddings, raw embeddings, or internal system credentials in client payloads. Only public `AlertView` DTO fields are transmitted.

## Consequences
- Gateway process remains stable and bounded in memory even under hostile or degraded network conditions.
- Strict isolation and protection against cross-site socket hijacking.
