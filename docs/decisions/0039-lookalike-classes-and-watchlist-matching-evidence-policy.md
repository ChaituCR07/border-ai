# ADR 0039: Look-Alike Classes, Watchlist Matching, and Evidence-Driven Change Policy

## Status
Accepted

## Context
Standard optical character recognition models frequently confuse visually similar characters under field surveillance conditions (such as motion blur, dust, angle perspective, and sensor noise). In Indian vehicle license plates, common visual ambiguities include:
- `0` $\leftrightarrow$ `O`, `Q`, `D`
- `1` $\leftrightarrow$ `I`
- `8` $\leftrightarrow$ `B`
- `5` $\leftrightarrow$ `S`
- `2` $\leftrightarrow$ `Z`
- `6` $\leftrightarrow$ `G`

In ADR 0023, BorderVision implemented `plate_key()` normalization to map look-alike character classes to canonical representations, enabling resilient watchlist lookups. However, these look-alike groupings were initial design assumptions. Changing them arbitrarily carries substantial risks: `plate_key` is implemented as a PostgreSQL `STORED` generated column with dedicated indexes across the production database, and is duplicated in Python and TypeScript runtimes.

## Decision

1. **Evidence-Driven Review Policy**:
   - The empirical character confusion matrix from dev and test evaluation sets serves as the sole ground truth evidence for evaluating look-alike classes.
   - A character substitution pair is:
     - **Retained**: If empirical support confirms optical confusion (or strong typographic justification exists without conflicting false matches).
     - **Considered for Addition**: If an unmapped substitution pair occurs with significant frequency ($\ge 15\%$ of substitutions with $n \ge 10$) without causing unacceptable collision spikes.
     - **Considered for Removal**: If a mapping produces high false alert collision rates while exhibiting zero positive true-match recoveries.

2. **Strict Multi-Tier Parity Rule for Schema Modifications**:
   - No character class may be added or removed in isolation.
   - Any modification requires simultaneous, atomic updates across all four implementations:
     1. Python matcher: `evaluation.anpr.metrics.plate_key()`
     2. PostgreSQL generated column: `database/migrations/*_plate_key.sql`
     3. TypeScript runtime: `shared/protocol/plate.ts`
     4. Shared parity fixtures: `docs/fixtures/plate_matching_cases.json`
   - All Day 18 cross-language parity tests must pass prior to merge.

3. **Database Migration Protocol**:
   - Because `plate_key` is a `STORED` generated column in PostgreSQL, modifying the SQL function does **not** automatically update existing records.
   - Any change requires a formal database migration that:
     1. Drops existing generated column and dependent indexes.
     2. Updates the SQL function definition.
     3. Re-adds the generated column (forcing a table rewrite across all historic vehicle reads).
     4. Rebuilds the B-Tree indexes.
   - Due to the operational cost of table rewrites, if empirical evidence indicates subtle confusion differences, **matcher weight tuning** in scoring algorithms is preferred over schema column changes.

4. **Tiered Watchlist Alert Policy**:
   - **Exact Matches** (`pred == watchlist`): Drive high-priority automated alerts and full `watchlist_vehicle` threat score.
   - **Look-Alike Only Matches** (`plate_key(pred) == plate_key(watchlist)` with `pred != watchlist`): Require temporal corroboration (multi-frame consensus votes $\ge 3$ or confidence $\ge 0.85$). Uncorroborated single-frame look-alike hits produce advisory warnings with a prominent visual "Look-Alike Equivalent" badge, preventing operator alert fatigue on large watchlists ($W \ge 1,000$).

## Consequences
- **Positive**: Prevents database corruption or cross-service desynchronization; guarantees reproducible evidence-backed character mappings; eliminates operator alert fatigue from loose look-alike matches.
- **Negative**: High barrier to altering character equivalence rules; requires formal migrations and table rewrites for schema updates.
