import csv
import logging
from pathlib import Path
from typing import Iterable

from app.watchlist.normalize import normalize_plate

log = logging.getLogger("behaviour")


class AuthorizedPlates:
    """A set of plates that are allowed (normalized the same way as recognized plates)."""

    def __init__(self, plates: Iterable[str] = ()):
        self._plates = {normalize_plate(p) for p in plates if p and p.strip()}

    @classmethod
    def from_csv(cls, path) -> "AuthorizedPlates":
        path = Path(path)
        if not path.exists():
            log.error("Authorized-plate list %s not found; treating the list as EMPTY", path)
            return cls()
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            column = "plate" if "plate" in (reader.fieldnames or []) else (reader.fieldnames or [None])[0]
            return cls(row[column] for row in reader if column and row.get(column))

    def contains(self, plate: str) -> bool:
        return normalize_plate(plate) in self._plates

    def __len__(self) -> int:
        return len(self._plates)
