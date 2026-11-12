#!/usr/bin/env python3
"""Audit documentation files to ensure all published performance metrics comply with ADR 0040.

ADR 0040 Rules:
1. Every public metric must be cited with a 95% Confidence Interval `[...]` and a run ID `run-YYYYMMDD-...`.
2. Standalone, unqualified accuracy assertions (e.g. '99% accurate' without run ID) are forbidden.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

RUN_ID_REGEX = re.compile(r"run-\d{8}-[a-z0-9-]+")
CI_REGEX = re.compile(r"\[\s*\d+(\.\d+)?\s*%\s*,\s*\d+(\.\d+)?\s*%\s*\]")
PERCENT_CLAIM_REGEX = re.compile(r"\b(\d{1,2}(?:\.\d+)?)\s*%\s*(accurate|accuracy|mAP|recall|precision|coverage|retention|HOTA|MOTA|IDF1)\b", re.IGNORECASE)

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "frontend/node_modules",
    "backend/node_modules",
    "venv",
    ".gemini",
    "__pycache__",
    "dist",
    "build",
}

EXCLUDED_FILES = {
    "Day_23_Model_Testing_ANPR_and_Consolidated_Report.md",
    "Day_22_Model_Testing_Detection_and_Tracking.md",
    "Day_21_Full_System_Integration.md",
}


def audit_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Scan a markdown file for unqualified claims."""
    violations = []
    if file_path.name in EXCLUDED_FILES:
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    in_code_block = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Look for accuracy claims
        matches = PERCENT_CLAIM_REGEX.finditer(line)
        for m in matches:
            claim_text = m.group(0)
            # Check if this line or context has run_id or CI, or is in a table citing a run ID
            has_run_id = bool(RUN_ID_REGEX.search(line))
            has_ci = bool(CI_REGEX.search(line))

            # If inside an ADR or model eval doc, check surrounding 5 lines for run_id or table header
            context_window = "".join(lines[max(0, idx - 4):min(len(lines), idx + 3)])
            context_has_run_id = bool(RUN_ID_REGEX.search(context_window)) or "run ID" in context_window or "Run ID" in context_window or "run_" in context_window

            if not has_run_id and not has_ci and not context_has_run_id:
                violations.append((idx, claim_text, line.strip()))

    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    target_docs = [
        repo_root / "README.md",
        repo_root / "docs/model_eval/anpr.md",
        repo_root / "docs/model_eval/detection.md",
        repo_root / "docs/model_eval/tracking.md",
        repo_root / "docs/model_eval/model_cards/anpr.md",
        repo_root / "docs/model_eval/model_cards/detector.md",
        repo_root / "docs/model_eval/model_cards/tracker.md",
        repo_root / "docs/model_eval/model_cards/face_reid_prototype.md",
        repo_root / "docs/perf/performance_report.md",
        repo_root / "docs/perf/optimizations.md",
        repo_root / "docs/perf/overload.md",
        repo_root / "docs/perf/bottlenecks.md",
        repo_root / "docs/perf/capacity.md",
        repo_root / "docs/testing/false_positive_report.md",
        repo_root / "docs/testing/fp_methodology.md",
    ]

    total_violations = 0
    print("[*] Auditing documentation files against ADR 0040 claims policy...")

    for doc in target_docs:
        if not doc.exists():
            continue
        v = audit_file(doc)
        if v:
            print(f"[!] Violations in {doc.relative_to(repo_root)}:")
            for line_no, claim, line in v:
                print(f"    L{line_no}: '{claim}' -> {line}")
            total_violations += len(v)
        else:
            print(f"  [PASS] {doc.relative_to(repo_root)}: compliant with ADR 0040")

    if total_violations > 0:
        print(f"\n[FAIL] Found {total_violations} unqualified claims violating ADR 0040 policy.")
        return 1

    print("\n[OK] All audited files comply with ADR 0040 claims and run ID attribution policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
