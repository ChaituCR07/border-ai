# ADR 0021 — Alert Notification Policy and Fatigue Mitigation

## Status
Accepted

## Context
High-frequency perimeter surveillance systems can produce bursts of alerts when vehicles or individuals trigger multiple tripwires or zone boundaries in rapid succession. Unconstrained notifications produce cognitive overload ("alarm fatigue"), causing operators to ignore or mute critical threat indicators.

## Decisions

1. **Severity-Tiered Notification Rules:**
   - **CRITICAL (Score $\ge 90$):**
     - Sticky toast overlay: remains visible until explicitly acknowledged or dismissed.
     - Screen reader announcement: assertive (`role="alert"`).
     - Audio chime: multi-frequency tone sequence (880 Hz – 660 Hz – 880 Hz).
     - Tab title indicator: displays count of unacknowledged critical alerts (e.g. `(2) 🚨 Border AI`).
   - **HIGH (Score 70–89):**
     - Auto-dismisses after 15 seconds.
     - Screen reader announcement: polite (`role="status"`).
     - Audio chime: softer single tone (660 Hz).
     - Hovering over toast pauses the auto-dismiss timer.
   - **MEDIUM & LOW (Score $< 70$):**
     - **No toast overlay and no audio notification.**
     - Appears directly in the alert feed and increments severity counter tiles.

2. **Burst Coalescing Window (20 seconds):**
   - Alerts arriving from the same `camera_id` with the same vehicle `plate` (or same `event_type` if no plate is detected) within a 20-second rolling window are coalesced into a single toast card.
   - The toast displays an explicit count badge (e.g. `×3`) and adopts the highest threat score observed during the burst.
   - If any coalesced alert in the burst is CRITICAL, the entire card becomes sticky.

3. **Visible Toast Cap:**
   - At most 3 toasts are visible simultaneously on the operational overlay.
   - Excess alerts are summarized in a "+N more alerts" badge.
   - CRITICAL toasts are always prioritized over HIGH toasts in visual order.

4. **Audio Ergonomics and Browser Autoplay Compliance:**
   - Audio synthesized via Web Audio oscillators (no external MP3/WAV assets to load or fail).
   - AudioContext requires explicit operator gesture (`unlockAudio()`) via a prominent "🔔 Enable Sound" header button.
   - Rate limiting: at most one audio sequence per 3-second window, even during high-velocity alert bursts.
   - Persistent user mute toggle stored in local client state.

5. **Cross-Terminal Synchronized Acknowledgment:**
   - When an operator acknowledges an alert in one session, the server broadcasts `alert.updated` with status `ACKNOWLEDGED`.
   - All other active browser sessions optimistically dismiss the corresponding toast and remove the alert from their open feed without page refresh.

6. **Silence on Reconnect Resync:**
   - Alerts fetched during bulk REST resynchronization **do not trigger individual toasts or audio chimes**.
   - Instead, a non-intrusive status banner announces: *"Connection restored: N alerts arrived while you were offline"*.

## Consequences
- Operators are immediately alerted to critical situations without sensory flooding.
- Consistent state maintained across multiple monitoring screens in the command center.
