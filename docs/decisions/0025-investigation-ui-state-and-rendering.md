# ADR 0025 — Investigation UI Architecture, URL State, and Virtualized Rendering

## Status
Accepted

## Context
The investigation dashboard is used for retrospective incident analysis, timeline tracking, and multi-camera journey reconstruction. Investigators need to share exact search states across shifts, navigate using browser history (`Back` / `Forward`), quickly filter multi-dimensional facets, and inspect high-density event streams without browser memory degradation or UI stutter.

## Decisions

1. **URL as Single Source of Truth:**
   - All investigation filters (`q`, `camera_id`, `event_type`, `severity`, `min_score`, `max_score`, `from`, `to`, `plate`, `plate_match`, `vehicle_id`, `person_id`, `time_from`, `time_to`, `tz`, `sort`, `view`, `selected_event_id`) are serialized directly into URL query parameters.
   - Investigation links can be copied, bookmarked, and shared between analysts with identical search results.
   - Browser navigation (`Back` / `Forward`) naturally undoes and redoes filter operations.
   - **Privacy Boundary:** The dialog `purpose` field is explicitly excluded from URL serialization to prevent sensitive case notes from leaking into browser history logs or shared URLs.

2. **Unified Omnibox with Structured Token Parsing:**
   - The omnibox acts as a hybrid natural language and structured query interface.
   - Supports key-value tokens: `cam:CAM-01`, `type:VEHICLE_DETECTED`, `sev:CRITICAL`, `score:>80`, `plate:KA01*`.
   - Free text automatically resolves to plates (if matching registration format), event IDs (if valid UUID), or full-text query `q`.
   - 250ms debounced typeahead suggestions hit `GET /api/investigation/suggest`.
   - Global keyboard shortcut `/` instantly focuses the omnibox from anywhere in the view.

3. **Disjunctive Facet Calculation:**
   - The facet endpoint `GET /api/investigation/facets` calculates filter counts disjunctively.
   - When a user filters by `camera_id=CAM-01`, the `by_camera` facet calculation deliberately removes the camera constraint, allowing other cameras to show their matching counts.
   - This prevents zero-count collapse and guides analysts toward productive filter refinements.

4. **DOM Virtualization for Massive Event Feeds:**
   - Results are rendered using `@tanstack/react-virtual` in `ResultsTable.tsx`.
   - Only active visible rows ($\approx 15$–$20$) plus a small overscan buffer ($\approx 10$) are mounted in the DOM.
   - DOM element count remains $< 60$ even when several thousand events are loaded in memory via keyset pagination.

5. **Pure Journey Reconstruction and Gap Representation:**
   - Vehicle journeys are reconstructed via pure functional logic (`buildJourney()`):
     - Chronological sorting with microsecond timestamp fidelity.
     - Collapsing consecutive events on the same camera within a 120-second threshold into single `Sighting` objects.
     - Preserving distinct visits if a camera is revisited later (A $\to$ B $\to$ A stays distinct).
     - Accurate gap calculation in seconds between consecutive camera sightings.
     - Plate variant tracking across sightings to flag OCR ambiguities to the investigator.

## Consequences
- High-performance, low-latency UI capable of handling multi-thousand event datasets smoothly.
- Shareable, repeatable forensic workflows across investigation teams.
- Seamless keyboard navigation (`/`, `j/k`, `Esc`) for rapid operational incident reviews.
