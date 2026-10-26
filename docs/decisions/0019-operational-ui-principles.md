# ADR 0019 — Operational UI Principles and Visual Ergonomics

## Status
Accepted

## Context
Command dashboards in perimeter and border security centers are operated 24/7 in varying lighting environments, often viewed from distances of 2 to 5 meters on wall-mounted multi-monitor displays or projectors. Standard web application UI patterns (e.g. relying solely on red/green colors, animations on every update, or ambiguous zero counts) induce operator fatigue and introduce critical perceptual failure modes.

## Decision
1. **Never Color Alone (Redundancy Principle):**
   - Severity is never indicated solely through hue. Every alert, event chip, and counter combines:
     - **Shape Icon:** ▲ for CRITICAL, ◆ for HIGH, ● for MEDIUM, ■ for LOW.
     - **Explicit Text Label:** "Critical", "High", "Medium", "Low".
     - **High-Contrast Token:** Contrast ratio $\ge 4.5:1$ against dark panel backgrounds (`#121821`, `#18212c`).
   - Ensures accessibility for color-blind operators and prevents washout on projectors.

2. **Freshness Transparency (Never Lie About State):**
   - When an API endpoint or stream connection drops, cached intelligence is retained rather than flashing empty or blank screens.
   - Cached data is immediately flagged with a visible `stale` badge and a sticky banner indicating the last known good update time (`formatTime(lastUpdated, tzMode)`).

3. **Actionable Counters (Tile vs List Consistency):**
   - The primary counter number on each severity tile displays **open, unacknowledged alerts** matching `open_alerts_by_priority`.
   - The secondary metric displays total events detected over the rolling 24-hour window (`severity_counts`).
   - Clicking a severity tile filters the alert feed to that exact priority; the count on the tile strictly equals the number of items in the filtered feed.

4. **Calm by Default (Reduced Motion & Attention Preservation):**
   - Ambient animations are strictly forbidden. Only active `OPEN CRITICAL` alerts exhibit a slow pulse indicator.
   - All animations strictly respect CSS `@media (prefers-reduced-motion: reduce)`.

5. **Explicit Temporal Representation:**
   - Every timestamp displays its time zone designation (`02:13:42 UTC` or `07:43:42 IST`).
   - JavaScript `Date` instances are restricted strictly to human presentation. ISO-8601 strings with full microsecond precision are preserved untouched for API filters, keyset cursors, and correlation IDs.

6. **Defense in Depth Against Insecure Rendering:**
   - User-influenced strings (license plates, track labels, annotation notes) are never rendered via raw HTML or unescaped templates (`dangerouslySetInnerHTML` is prohibited).

## Consequences
- Operator cognitive load is minimized during prolonged monitoring shifts.
- Projector washout, color blindness, and network degradation do not compromise situational awareness.
