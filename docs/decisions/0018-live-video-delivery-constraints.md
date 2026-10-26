# ADR 0018 — Live Video Delivery Constraints and Connection Safety

## Status
Accepted

## Context
Standard browsers restrict concurrent HTTP/1.1 connections to approximately 6 per origin. Because multipart MJPEG video streams hold persistent, indefinitely open HTTP connections, streaming 4 to 6 cameras simultaneously from the same origin can exhaust available browser connection pools, completely starving API polling requests, metrics fetching, and operator acknowledgements.

## Decision
1. **Hard Upper Bound on Active Streams:**
   - The frontend enforces a maximum of **4 concurrent active video streams** at any moment:
     - `1x1` layout: Exactly 1 stream connection active.
     - `2x2` layout: At most 4 streams active (top-left selected camera + next 3 enabled cameras).
   - Cameras not displayed in the viewport maintain zero active HTTP connections.

2. **Connection Teardown on Unmount and Tab Concealment:**
   - Unmounting or switching cameras explicitly resets `img.src` to a 1x1 blank base64 GIF (`data:image/gif;base64,...`) to force browsers to close the underlying socket immediately.
   - When the user switches tabs or minimizes the window, `useDocumentVisible` detects `document.visibilityState === 'hidden'`, pauses all active video connections, and restores them only when the document returns to visible.

3. **Separate Origin Architecture:**
   - Video streaming originates from the Day 7 MJPEG server (`:8001`), whereas API calls target `:4000` (or the Vite proxy `/api`). The separation of origins prevents video streams from competing directly with REST API connection pools under HTTP/1.1. Full HTTP/2 multiplexing via reverse proxy is deferred to Day 27.

4. **Exponential Reconnection Backoff with Jitter:**
   - If a video stream disconnects or fails, `MjpegPlayer` schedules retries using exponential backoff with equal jitter:
     $$T_{\text{backoff}} = \text{clamp}(1000 \cdot 2^{\text{attempt}}, 1000, 15000)$$
   - Prevents thundering-herd reconnect spikes against the FrameHub streaming server upon brief network dropouts.

## Consequences
- Guaranteed zero connection starvation for REST/WebSocket control channels.
- CPU and network bandwidth preserved when the dashboard tab is in the background.
- Stream connection leaks are prevented during rapid camera switching.
