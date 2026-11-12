"""Exposure ledger parser, validator, and unique camera-hour calculator.

Strictly enforces:
- Unique clip IDs (no duplicates permitted).
- Zero loop inflation (loops == 1 required for every entry).
- Disjoint dev and held-out partition membership.
- Positive unique duration in seconds.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass(frozen=True)
class ExposureEntry:
    source: str
    clip_id: str
    camera: str
    unique_duration_s: float
    loops: int
    conditions: str
    licence: str
    split: str
    used_for: str

    @property
    def camera_hours(self) -> float:
        return self.unique_duration_s / 3600.0


REQUIRED_COLUMNS = [
    "source",
    "clip_id",
    "scene/camera",
    "unique_duration_s",
    "loops",
    "conditions",
    "licence",
    "split",
    "used_for",
]


class ExposureLedger:
    def __init__(self, entries: List[ExposureEntry]):
        self.entries = entries

    @classmethod
    def load(cls, path: str | Path) -> ExposureLedger:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Exposure ledger not found at {p}")

        entries: List[ExposureEntry] = []
        seen_clips: Set[str] = set()

        with open(p, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("Exposure ledger CSV is empty")

            missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise ValueError(f"Missing required columns in exposure ledger: {missing}")

            for line_no, row in enumerate(reader, start=2):
                clip_id = row["clip_id"].strip()
                if not clip_id:
                    raise ValueError(f"Empty clip_id on line {line_no}")
                if clip_id in seen_clips:
                    raise ValueError(f"Duplicate clip_id '{clip_id}' on line {line_no}; each clip must be unique")
                seen_clips.add(clip_id)

                try:
                    dur = float(row["unique_duration_s"])
                except ValueError:
                    raise ValueError(f"Invalid unique_duration_s '{row['unique_duration_s']}' on line {line_no}")
                if dur <= 0.0:
                    raise ValueError(f"Duration must be strictly positive on line {line_no}, got {dur}")

                try:
                    loops = int(row["loops"])
                except ValueError:
                    raise ValueError(f"Invalid loops integer '{row['loops']}' on line {line_no}")
                if loops != 1:
                    raise ValueError(
                        f"Non-unit loops ({loops}) on line {line_no}; looped footage cannot be counted as unique exposure"
                    )

                split = row["split"].strip().lower()
                if split not in {"dev", "held-out", "test"}:
                    raise ValueError(f"Invalid split '{split}' on line {line_no}; must be 'dev', 'held-out', or 'test'")

                entry = ExposureEntry(
                    source=row["source"].strip(),
                    clip_id=clip_id,
                    camera=row["scene/camera"].strip(),
                    unique_duration_s=dur,
                    loops=loops,
                    conditions=row["conditions"].strip(),
                    licence=row["licence"].strip(),
                    split=split,
                    used_for=row["used_for"].strip(),
                )
                entries.append(entry)

        return cls(entries)

    def total_camera_hours(self, split: str | None = None) -> float:
        """Calculate total unique exposure in camera-hours, optionally filtered by split."""
        selected = self.entries if split is None else [e for e in self.entries if e.split == split.lower()]
        return sum(e.camera_hours for e in selected)

    def hours_by_split(self) -> Dict[str, float]:
        res: Dict[str, float] = {}
        for e in self.entries:
            res[e.split] = res.get(e.split, 0.0) + e.camera_hours
        return res

    def hours_by_source(self) -> Dict[str, float]:
        res: Dict[str, float] = {}
        for e in self.entries:
            res[e.source] = res.get(e.source, 0.0) + e.camera_hours
        return res

    def hours_by_camera(self) -> Dict[str, float]:
        res: Dict[str, float] = {}
        for e in self.entries:
            res[e.camera] = res.get(e.camera, 0.0) + e.camera_hours
        return res
