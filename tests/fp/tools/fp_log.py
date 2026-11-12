"""False-positive triage log validator and root-cause classifier.

Enforces:
- Closed cause taxonomy validation.
- Separation of ground-truth labeling errors (gt_error == 'yes') from true system FPs.
- Standardized triage status lifecycle (TRIAGED, MITIGATED, ACCEPTED_LIMITATION).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

VALID_CAUSES: Set[str] = {
    "detector_ghost",
    "class_confusion",
    "foot_point_perspective",
    "tracker_jitter",
    "id_switch_duplicate",
    "hysteresis_too_small",
    "rule_logic_bug",
    "ocr_misread",
    "lookalike_match",
    "scene_or_camera_shift",
    "lighting_or_weather",
    "compression_artifact",
    "gt_error",
    "unknown",
}

VALID_STATUSES: Set[str] = {
    "TRIAGED",
    "MITIGATED",
    "ACCEPTED_LIMITATION",
    "INVESTIGATING",
}

REQUIRED_COLUMNS = [
    "fp_id",
    "run_id",
    "clip_id",
    "t_clip_s",
    "rule/event",
    "tier",
    "subject",
    "cause",
    "gt_error",
    "status",
    "mitigation_ref",
    "notes",
]


@dataclass(frozen=True)
class FpLogEntry:
    fp_id: str
    run_id: str
    clip_id: str
    t_clip_s: float
    rule_or_event: str
    tier: str
    subject: str
    cause: str
    gt_error: bool
    status: str
    mitigation_ref: str
    notes: str


class FpLog:
    def __init__(self, entries: List[FpLogEntry]):
        self.entries = entries

    @classmethod
    def load(cls, path: str | Path) -> FpLog:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"FP triage log not found at {p}")

        entries: List[FpLogEntry] = []
        with open(p, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("FP triage log is empty")

            missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise ValueError(f"Missing columns in triage log: {missing}")

            for line_no, row in enumerate(reader, start=2):
                fp_id = row["fp_id"].strip()
                if not fp_id:
                    raise ValueError(f"Empty fp_id on line {line_no}")

                cause = row["cause"].strip().lower()
                if cause not in VALID_CAUSES:
                    raise ValueError(f"Invalid cause '{cause}' on line {line_no}; must be in {VALID_CAUSES}")

                gt_raw = row["gt_error"].strip().lower()
                if gt_raw not in {"yes", "no"}:
                    raise ValueError(f"gt_error must be 'yes' or 'no' on line {line_no}, got '{gt_raw}'")
                gt_error = (gt_raw == "yes")

                status = row["status"].strip().upper()
                if status not in VALID_STATUSES:
                    raise ValueError(f"Invalid status '{status}' on line {line_no}; must be in {VALID_STATUSES}")

                try:
                    t_s = float(row["t_clip_s"])
                except ValueError:
                    raise ValueError(f"Invalid t_clip_s on line {line_no}: '{row['t_clip_s']}'")

                entry = FpLogEntry(
                    fp_id=fp_id,
                    run_id=row["run_id"].strip(),
                    clip_id=row["clip_id"].strip(),
                    t_clip_s=t_s,
                    rule_or_event=row["rule/event"].strip(),
                    tier=row["tier"].strip().upper(),
                    subject=row["subject"].strip(),
                    cause=cause,
                    gt_error=gt_error,
                    status=status,
                    mitigation_ref=row["mitigation_ref"].strip(),
                    notes=row["notes"].strip(),
                )
                entries.append(entry)

        return cls(entries)

    def genuine_fps(self) -> List[FpLogEntry]:
        """Returns false positives excluding ground-truth errors."""
        return [e for e in self.entries if not e.gt_error]

    def gt_errors(self) -> List[FpLogEntry]:
        """Returns entries where the system was correct but ground-truth was faulty."""
        return [e for e in self.entries if e.gt_error]

    def cause_counts(self, tier: str | None = None) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.genuine_fps():
            if tier is None or e.tier == tier.upper():
                counts[e.cause] = counts.get(e.cause, 0) + 1
        return counts

    def tier_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.genuine_fps():
            counts[e.tier] = counts.get(e.tier, 0) + 1
        return counts
