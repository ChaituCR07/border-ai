# Watchlist System Guide

The Watchlist system monitors recognized license plates (and future face/person entities) against an operational database, raising real-time alerts and flagging suspect tracks on live video streams.

---

## 1. Schema & Architecture

The database layer consists of three core tables managed via idempotent migration `database/migrations/001_watchlist.sql`:

1. `watchlist`: Primary entries for `VEHICLE`, `PLATE`, `PERSON`, and `FACE`.
   - Unique partial index: `(entity_type, normalized_identifier) WHERE active`.
   - Length index: `(char_length(normalized_identifier)) WHERE active`.
2. `watchlist_audit`: Immutable change log recording `ADD`, `UPDATE`, `DEACTIVATE`, `RESTORE`, and `IMPORT` actions along with actor identity and payload diffs.
3. `watchlist_hits`: Event log of every match (including suppressed repeat hits) with scoring, confidence, camera, and track correlation.

```
Detected Plate (ANPR Worker)
         │
         ▼
  PLATE_RECOGNIZED Event ──► Pipeline Queue
                                  │
                                  ▼
                         Watchlist Worker Thread
                                  │
                      PostgreSQL Lookup (find_exact / find_same_length)
                     (Transparent Fallback to In-Memory Snapshot if DB Down)
                                  │
                                  ▼
                              Match?
                             /      \
                           No        Yes
                            │          │
                          Stop    Score = 100 * conf * quality
                                  Status = alert | review
                                       │
                                  Cooldown Check ──► Suppressed? (Store hit, skip event)
                                       │
                                    Active
                                       │
                           Emit WATCHLIST_MATCH Event
                           Store Hit in watchlist_hits
                           Flag Track (Red Box + WATCHLIST Banner on Video)
```

---

## 2. CLI Usage

The management CLI is located at `ai-engine/scripts/watchlist_cli.py`:

```bash
# Initialize schema migrations
python ai-engine/scripts/watchlist_cli.py init

# Seed synthetic demo entries (KA01AB1234, MH12XY4321, DL08CZ9999)
python ai-engine/scripts/watchlist_cli.py seed-demo

# List active entries
python ai-engine/scripts/watchlist_cli.py list

# Test what happens if a plate is recognized
python ai-engine/scripts/watchlist_cli.py check KA01AB1234 --confidence 0.91
# Output: KA01AB1234: exact match with #1 (HIGH), distance 0.0, score 91, status alert

python ai-engine/scripts/watchlist_cli.py check KA01AB1284 --confidence 0.91
# Output: KA01AB1284: near match with #1 (HIGH), distance 1.0, score 73, status review

python ai-engine/scripts/watchlist_cli.py check MH99ZZ0001
# Output: MH99ZZ0001: no match

# Inspect hits and audit logs
python ai-engine/scripts/watchlist_cli.py hits --limit 10
python ai-engine/scripts/watchlist_cli.py audit --limit 10
```

---

## 3. Matching & Scoring Rules

- **Exact Match:** Stored normalized identifier equals recognized plate. Distance = 0.0, Quality = 1.0. Score = $100 \times \text{plate\_confidence}$. Status is `alert` if $\text{confidence} \ge \text{alert\_min\_confidence}$ (0.70), else `review`.
- **Near Match:** Same character length with OCR-aware distance $\le 1.0$.
  - Look-alike substitution (`B/8`, `O/0`, `1/I`, `S/5`, `Z/2`): cost = 0.5.
  - Standard substitution: cost = 1.0.
  - Quality = $1.0 - 0.2 \times \text{distance}$.
  - Status defaults to `review`.

---

## 4. Simulation & Outage Resilience

- **Simulation (`scripts/watchlist_simulate.py`):**
  - Tested against 200 listed plates and 2,000 unlisted plates across confidence tiers.
  - False positive rate on random unlisted plates is 0.0%.
  - High confidence exact hits trigger `alert` 100% of the time.
  - Ambiguous near reads (e.g. OCR single digit slips) trigger `review` and never cause false definitive alerts.

- **Outage Drill:**
  1. Stopping the PostgreSQL container (`docker compose stop postgres`) switches `db_ok` to `false`.
  2. The service continues matching using its in-memory snapshot, successfully raising `WATCHLIST_MATCH` events.
  3. Hit records are queued in memory (`hits_unsaved`).
  4. Upon database recovery (`docker compose start postgres`), the worker flushes unsaved hits into `watchlist_hits` and restores `db_ok: true`.
  5. Setting `watchlist.require_db: true` ensures the pipeline refuses to boot if the database is unavailable at startup.
