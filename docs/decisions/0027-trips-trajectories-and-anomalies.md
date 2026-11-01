# ADR 0027 — Trips, Trajectories, Greedy Assignment, and Anomaly Taxonomy

## Status
Accepted

## Context
A vehicle may be observed dozens of times over days or weeks. Stacking all sightings into a single monolithic journey conflates separate trips and masks anomalies. Furthermore, when two identical license plates are detected concurrently on distant roads (e.g., cloned license plates or misreads), a correlation engine must separate them into distinct physical trajectories rather than crashing or merging them into nonsensical paths.

## Decisions

1. **Trip Segmentation:**
   - Chronological sightings are partitioned into trips based on time gaps exceeding `trip_break_s` (default 21,600 s / 6 hours).
   - Each trip is given an identifier `trip-1`, `trip-2`, etc.
   - Gaps `<= 6` hours are retained within the same trip.

2. **Greedy Trajectory Assignment:**
   - Within each trip, sightings are assigned greedily to the trajectory that fits best:
     - Candidate links that are `IMPOSSIBLE` or `SIMULTANEOUS` are rejected.
     - Candidate links with confidence `< min_link_confidence` (0.3) are rejected.
     - Ties between valid candidate trajectories are resolved deterministically by:
       1. Higher link confidence.
       2. Fewer missed cameras (preferring routes with 0 missed cameras).
       3. Closeness to typical travel time ($|\text{gap} - \text{typical\_s}|$).
       4. Recency of last sighting on that trajectory (`lastSeen(t)`).
   - If a sighting cannot attach to any existing trajectory, a new trajectory (`T1`, `T2`, etc.) is spawned.
   - Total trajectories per trip are capped at `max_trajectories` (4). Excess sightings trigger `TRAJECTORY_OVERFLOW`.

3. **Anomaly Taxonomy:**
   - **`IMPOSSIBLE_TRAVEL` (warning):** Sighting cannot attach because travel time is far faster than the fastest route.
   - **`SIMULTANEOUS_SIGHTINGS` (warning):** Negative time gap observed between non-overlapping cameras.
   - **`MULTIPLE_TRAJECTORIES` (warning):** A trip contains $\ge 2$ trajectories. The UI displays the alert banner: *"This plate appears on N incompatible trajectories — possible duplicated plate or misread. This is a lead, not a conclusion."*
   - **`MISSED_CAMERA` (info):** Every consistent route passes through camera $X$, but $X$ observed no sighting.
   - **`SLOW_TRANSIT` (info):** Travel time significantly exceeded expected maximum.
   - **`FAST_TRANSIT` (info):** Travel time was faster than expected min but within tolerance.
   - **`UNLINKED_HOP` (info):** Hop traversed between cameras with no link in topology.
   - **`TRAJECTORY_OVERFLOW` (warning):** Number of incompatible trajectories exceeded `max_trajectories`.

4. **Zero Mutation & Determinism Guarantees:**
   - The correlation engine never mutates input arrays or sighting objects.
   - Shuffled inputs across 100 random permutations produce byte-identical JSON outputs.
   - Tie-breaks on identical `first_seen` timestamps are totally ordered by camera ID and event ID.

## Consequences
- Multi-day commuters cleanly segment into distinct trips.
- Cloned plates and misreads separate into distinct, readable trajectories.
- Total determinism guarantees reproducible results in court and forensic audits.

