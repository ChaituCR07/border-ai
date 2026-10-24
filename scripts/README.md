# Automation & Operational Scripts (`scripts`)

The Border AI platform provides automation, operational maintenance, and offline evaluation scripts located across the root `scripts/` directory and `ai-engine/scripts/`.

---

## 1. Directory Structure

```text
border-ai/
├── scripts/
│   └── setup.sh                   # Scaffolds directory hierarchy and placeholders
└── ai-engine/scripts/
    ├── run_pipeline.py            # End-to-end multi-threaded analytics pipeline runner
    ├── threat_calc.py             # Threat scoring math calculator and scenario validator
    ├── score_replay.py            # Offline event log threat scoring replay and tuning
    ├── rules_check.py             # Behaviour rules and scoring sources validator
    ├── replay_behaviour.py        # Offline behaviour rule replay without GPU
    ├── check_events.py            # Ground-truth event count and type verification
    ├── watchlist_cli.py           # Watchlist administration and inspection CLI
    ├── face_enroll.py             # Consent-gated facial biometric enrollment utility
    ├── face_eval.py               # Genuine vs. impostor face verification benchmark
    ├── reid_eval.py               # Cross-camera appearance Re-ID evaluation
    └── view_cameras.py            # Multi-camera live grid viewer with telemetry
```

---

## 2. Core Operational Utilities

### 2.1 Full Analytics Pipeline (`run_pipeline.py`)
Executes the unified vision pipeline (Ingestion + Detection + ByteTrack + Spatial Rules + ANPR + Watchlist + Face/Re-ID + Behaviour Engine + Threat Scorer + Evidence Snapshots):
```bash
cd ai-engine
python scripts/run_pipeline.py \
    --source ../datasets/videos/person_walking.mp4 \
    --camera-id CAM_001 \
    --clock-start 2026-10-12T02:13:00
```
- `--no-scoring`: Disables the threat scoring engine.
- `--no-snapshots`: Disables evidence JPEG snapshot generation.
- `--clock-start <ISO>`: Sets a simulated starting clock for offline reproducibility.

### 2.2 Threat Calculator (`threat_calc.py`)
Validates hypothetical evidence combinations against the scoring table without video:
```bash
cd ai-engine
# Validate Plan Scenario 1 and Scenario 2 arithmetic
python scripts/threat_calc.py --plan

# Test arbitrary combinations
python scripts/threat_calc.py watchlist_vehicle:alert zone_violation direction_violation after_hours
```

### 2.3 Threat Score Replay (`score_replay.py`)
Streams recorded `events.jsonl` files through the threat scorer with new weights or windows:
```bash
cd ai-engine
python scripts/score_replay.py --events ../outputs/runs/<run_id>/events.jsonl --tick 1.0
```

### 2.4 Rules & Scoring Consistency Checker (`rules_check.py`)
Validates syntax in `configs/rules.json`, displays enabled behaviour rules and scoring sources, and warns of any unlinked events:
```bash
cd ai-engine
python scripts/rules_check.py
```

### 2.5 Watchlist Administration (`watchlist_cli.py`)
CLI interface for managing operational watchlist entries in PostgreSQL:
```bash
cd ai-engine
# Add vehicle plate entry
python scripts/watchlist_cli.py add KA01AB1234 --type VEHICLE --risk CRITICAL --notes "Stolen SUV"

# Lookup plate
python scripts/watchlist_cli.py lookup KA01AB1234

# List active entries
python scripts/watchlist_cli.py list --active-only
```

### 2.6 Face Biometric Enrollment (`face_enroll.py`)
Enrolls consenting individuals into the face watchlist with mandatory consent confirmation:
```bash
cd ai-engine
python scripts/face_enroll.py \
    --folder path/to/photos/ \
    --identifier subject-001 \
    --name "Officer John" \
    --risk LOW \
    --consent-confirmed
```

### 2.7 Event Processor Daemon (`run_event_processor.py`)
Runs the streaming event processor worker that reads from Redis Streams and routes to registered sinks:
```bash
cd ai-engine
python scripts/run_event_processor.py --consumer worker-1 --out ../outputs/processed/events.jsonl
```

### 2.8 Stream Monitoring & Lag Inspection (`stream_stats.py`)
Prints active stream lengths, consumer groups, pending unacknowledged entries, and consumer lag:
```bash
cd ai-engine
python scripts/stream_stats.py
```

### 2.9 Stream Real-Time Tailing (`stream_tail.py`)
Tails live stream entries or inspects dead-letter queues:
```bash
cd ai-engine
# Tail live events stream
python scripts/stream_tail.py --stream events --follow

# Inspect dead-letter messages with failure reasons
python scripts/stream_tail.py --stream dead --count 20
```

### 2.10 Offline Journal Replay (`replay_journal.py`)
Replays a local disk journal (`events.jsonl`) to Redis Streams after edge network restoration:
```bash
cd ai-engine
python scripts/replay_journal.py --events ../outputs/runs/run_20261022_120000/events.jsonl --rate 500
```

### 2.11 Camera Inventory Seeding (`seed_cameras.py`)
Seeds or updates camera inventory from `configs/cameras.json` into the PostgreSQL `cameras` table:
```bash
cd ai-engine
python scripts/seed_cameras.py
```

### 2.12 Database Table Statistics & Counters (`db_stats.py`)
Prints table row counts and breakdown of active alerts by priority and workflow status:
```bash
cd ai-engine
python scripts/db_stats.py
```

### 2.13 Policy-Driven Data Retention (`db_retention.py`)
Executes retention cleanup of historical events and resolved alerts by age threshold:
```bash
cd ai-engine
# Dry-run inspection
python scripts/db_retention.py --events-days 30 --alerts-days 365

# Execute deletion
python scripts/db_retention.py --events-days 30 --alerts-days 365 --yes
```
