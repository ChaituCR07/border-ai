import csv
from pathlib import Path
from typing import List, Tuple

from app.watchlist.models import DuplicateEntry, InvalidEntry

FIELDS = ["entity_type", "identifier", "name", "risk_level", "description"]


def import_csv(repo, path, actor: str = "import") -> Tuple[int, int, List[str]]:
    """Add entries from a CSV with the columns above. Returns (added, skipped_duplicates, error_messages).
    Bad rows are reported with their line number and do not stop the import."""
    added, skipped, errors = 0, 0, []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ("entity_type", "identifier", "name", "risk_level") if c not in (reader.fieldnames or [])]
        if missing:
            return 0, 0, [f"missing columns: {missing}"]
        for line_no, row in enumerate(reader, start=2):
            try:
                repo.add(row["entity_type"], row["identifier"], row["name"], row["risk_level"],
                         row.get("description") or "", actor=actor)
                added += 1
            except DuplicateEntry:
                skipped += 1
            except InvalidEntry as e:
                errors.append(f"line {line_no}: {e}")
    return added, skipped, errors


def export_csv(repo, path, active_only: bool = True) -> int:
    entries = repo.list_entries(active_only=active_only, limit=100000)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for e in entries:
            writer.writerow({"entity_type": e.entity_type, "identifier": e.identifier, "name": e.name,
                             "risk_level": e.risk_level, "description": e.description})
    return len(entries)
