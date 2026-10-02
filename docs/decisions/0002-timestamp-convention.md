# ADR 0002: Timestamp Convention Across Pipeline and Cameras

## Context
When processing video streams from a heterogeneous combination of live RTSP feeds and pre-recorded test video files, timestamp drift and timezone ambiguity can corrupt cross-camera correlation, threat scoring timelines, and event ordering.

## Decision
1. **Wall-clock UTC epoch timestamp:**
   - Every emitted `Frame` contains `timestamp = time.time()` representing the wall-clock UTC epoch seconds at the moment the frame was captured/read.
   - All spatial analytics, zone entry events, virtual line crossings, ANPR reads, and threat scoring alerts derive from this single timeline.
2. **Video container offset (`video_time_ms`):**
   - Stored independently to represent the native playback position inside a video file (useful for forensic replay and debugging). For live RTSP streams, it is `0.0`.
3. **UTC Boundary Formatting:**
   - Timestamps are serialized as ISO 8601 UTC strings (`YYYY-MM-DDTHH:MM:SS.sssZ`) only at output boundaries (JSON schemas, PostgreSQL tables, Redis payloads, and UI WebSockets). Local time strings are never stored or processed internally.

## Consequences
- Guaranteed cross-camera temporal consistency.
- Zero timezone confusion across server, database, and client dashboards.
