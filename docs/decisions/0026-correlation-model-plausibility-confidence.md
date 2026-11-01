# ADR 0026 — Camera Topology Graph, Link Plausibility, and Explainable Confidence

## Status
Accepted

## Context
In automated border surveillance, observing a vehicle at multiple camera locations produces a chronological sequence of sightings. However, treating every chronological sighting as equally valid ignores the physical camera network layout, road topography, and travel feasibility. A vehicle sighted at two distant checkpoints within 60 seconds is physically impossible and indicates either duplicate/cloned license plates or an ANPR OCR misread. Furthermore, operators require transparent, explainable confidence scores for every cross-camera hop rather than opaque machine-learning probabilities.

## Decisions

1. **Schematic Camera Topology Graph (`TopologyIndex`):**
   - Camera nodes have normalized schematic coordinates `(map_x, map_y)` within a `[0, 100]` grid, enabling clean SVG rendering without external mapping tile providers or GPS dependencies.
   - Edges define physical roadway links with `min_s` (fastest transit), `typical_s` (standard travel time), `max_s` (maximum expected transit), `direction` (`both` or `a_to_b`), and `overlap` (whether coverage fields overlap).
   - Graph traversal enumerates simple acyclic paths up to `maxHops = 4`.
   - To guard against graph explosion on dense networks, routes per camera pair are capped at 20 (`maxRoutesPerPair = 20`), sorted deterministically by `typical_s` and camera sequence.
   - Deterministic `canonicalVersion` SHA-1 hash is computed over canonical sorted link tuples.

2. **Eight Plausibility Classes:**
   - `REVISIT`: Consecutive sightings at the same camera.
   - `PLAUSIBLE`: Transit time between cameras falls within expected bounds (`min_s` to `max_s`).
   - `FAST`: Transit time is faster than `min_s` but within acceptable tolerance (`>= speed_tolerance * min_s`, default 0.8).
   - `SLOW`: Transit time exceeds `max_s` (`> max_s`).
   - `IMPOSSIBLE`: Transit time is significantly faster than the fastest possible route (`< speed_tolerance * min_s`).
   - `SIMULTANEOUS`: Sighting occurred before leaving previous camera (`gap < 0`) on non-overlapping cameras.
   - `OVERLAP_OK`: Small negative gap between overlapping camera fields (`gap >= -overlap_tolerance_s`).
   - `UNLINKED`: No route exists in the topology connecting the two cameras.

3. **Multiplicative Explainable Confidence Model:**
   - Link confidence is computed as:
     $$\text{link\_confidence} = \text{plate\_factor} \times \text{timing\_factor} \times \text{appearance\_factor}$$
   - **Plate factor:** Exact match = 1.0; look-alike variant match = 0.7; unknown quality = 1.0.
   - **Timing factor:**
     - Inside typical band (`[0.75 * typical_s, 1.5 * typical_s]`) = 1.0
     - In-range (`min_s` to `max_s`, outside typical band) = 0.7
     - Fast hop = 0.5
     - Slow transit = 0.6 (`<= 3 * max_s`) or 0.4 (`> 3 * max_s`)
     - Unlinked hop = 0.4
     - Impossible / simultaneous = 0.0
   - Every factor preserves human-readable `detail` explaining its evaluation.

4. **Strict Missed Camera Detection:**
   - A checkpoint camera $X$ is flagged as `missed_cameras` if and only if **every** topologically consistent route between checkpoint $A$ and checkpoint $B$ passes through $X$ and $X$ recorded no sighting. If a bypass road exists, $X$ is never falsely flagged.

## Consequences
- Physical feasibility is strictly enforced across camera transits.
- Explainable confidence factors eliminate black-box decision making.
- Missing checkpoints and cloned plates are surfaced immediately as investigative leads.

