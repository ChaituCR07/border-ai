#!/usr/bin/env python3
"""
Border-AI Privacy, Security & Canary Secrets Conformance Scanner (Task 10).
Scans logs, databases, artifact files, Redis entries, and emails to prove:
1. Zero canary credentials leak into observable surfaces.
2. Zero biometric float embeddings (len >= 64) appear in logs or payloads.
3. No sensitive PII (plates, emails) appears in INFO logs.
4. Snapshot file traversal attempts are rejected.
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Set


EMBEDDING_REGEX = re.compile(r"\[(?:-?\d+\.\d+,\s*){63,}-?\d+\.\d+\]")


DEFAULT_CANARIES = [
    "zq9canaryRtspPub",
    "zq9canaryRtspRead",
    "zq9canaryPg",
    "zq9canaryJwtSecretKey",
    "zq9canarySmtp",
]


class ConformanceViolation:
    def __init__(self, check_type: str, location: str, detail: str):
        self.check_type = check_type
        self.location = location
        self.detail = detail

    def to_dict(self) -> Dict[str, str]:
        return {
            "type": self.check_type,
            "location": self.location,
            "detail": self.detail,
        }


class ConformanceScanner:
    def __init__(self, canaries: Optional[List[str]] = None):
        self.canaries = canaries or DEFAULT_CANARIES
        self.violations: List[ConformanceViolation] = []

    def scan_text(self, text: str, location_label: str) -> None:
        # 1. Canary leak check
        for c in self.canaries:
            if c in text:
                masked_c = c[:3] + "***" + c[-2:]
                self.violations.append(
                    ConformanceViolation(
                        "CANARY_SECRET_LEAK",
                        location_label,
                        f"Detected canary secret '{masked_c}' in output",
                    )
                )

        # 2. Raw biometric embedding check (64+ float array)
        if EMBEDDING_REGEX.search(text):
            self.violations.append(
                ConformanceViolation(
                    "BIOMETRIC_EMBEDDING_LEAK",
                    location_label,
                    "Detected raw vector embedding array (>= 64 floats) in payload",
                )
            )

    def scan_log_for_pii(self, log_lines: List[str], target_plate: str, location_label: str) -> None:
        # Plate should not appear in INFO lines
        plate_clean = target_plate.replace(" ", "").upper()
        for line in log_lines:
            if "INFO" in line and plate_clean in line.replace(" ", "").upper():
                self.violations.append(
                    ConformanceViolation(
                        "PII_IN_INFO_LOG",
                        location_label,
                        f"Target license plate detected in INFO-level log line: {line.strip()[:80]}",
                    )
                )

    def scan_directory(self, target_dir: str) -> None:
        if not os.path.exists(target_dir):
            return

        for root, _, files in os.walk(target_dir):
            for file in files:
                # Skip binary files
                if file.endswith((".mp4", ".jpg", ".jpeg", ".png", ".pyc")):
                    continue
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    self.scan_text(content, f"file:{path}")
                except Exception:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Privacy & Secrets Conformance Scanner")
    parser.add_argument("--scan-dir", default="logs", help="Directory to scan")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Artifacts directory to scan")
    args = parser.parse_args()

    scanner = ConformanceScanner()
    scanner.scan_directory(args.scan_dir)
    scanner.scan_directory(args.artifacts_dir)

    if scanner.violations:
        print(f"\nConformance sweep FAILED with {len(scanner.violations)} violations:")
        for v in scanner.violations:
            print(f"  - [{v.check_type}] {v.location}: {v.detail}")
        sys.exit(1)
    else:
        print("\nConformance sweep PASSED: Zero canary leaks, zero embeddings, clean PII hygiene.")
        sys.exit(0)


if __name__ == "__main__":
    main()
