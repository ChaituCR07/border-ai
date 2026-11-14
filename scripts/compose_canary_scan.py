#!/usr/bin/env python3
"""
Canary Secret Leak Scanner for Border-AI Deployments
Scans configuration files, compose manifests, Dockerfiles, and runtime configurations
to ensure confidential passwords, master keys, and private keys never leak into production code.
"""

import os
import re
import sys
from typing import List, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CANARY_PATTERNS = [
    (r"-----BEGIN (?:RSA |OPENSSH |ED25519 |EC )?PRIVATE KEY-----\s*[A-Za-z0-9+/=]{20,}", "Unencrypted private key block detected"),
    (r"POSTGRES_PASSWORD\s*[:=]\s*(?!/|['\"]\$\{|your_|test|change_me|<)[a-zA-Z0-9_\-\.\!@#\$%\^&\*]{6,}", "Hardcoded production PostgreSQL password"),
    (r"REDIS_PASSWORD\s*[:=]\s*(?!/|['\"]\$\{|your_|test|change_me|<)[a-zA-Z0-9_\-\.\!@#\$%\^&\*]{6,}", "Hardcoded production Redis password"),
    (r"MASTER_KEY\s*[:=]\s*(?!/|['\"]\$\{)[a-fA-F0-9]{64}", "Hardcoded AES-256 master key"),
    (r"CANARY_SECRET_LEAK_TEST_TOKEN", "Synthetic test canary detected"),
]

IGNORED_DIRS = {
    ".git", ".github", ".venv", "node_modules", "secrets", "certs",
    "backups", "outputs", "dist", "build", "project -plans", "project-plans"
}
SCANNED_EXTENSIONS = {".yml", ".yaml", ".json", ".conf", ".sh", ".ts", ".js", ".py", ".md", "Dockerfile"}

def scan_text(content: str, source_path: str) -> List[Tuple[str, int, str]]:
    findings = []
    # Test multiline pattern on entire content first
    for pattern, desc in CANARY_PATTERNS:
        matches = re.finditer(pattern, content)
        for m in matches:
            line_idx = content[:m.start()].count("\n") + 1
            findings.append((source_path, line_idx, desc))
    return findings

def scan_repository(root_dir: str) -> List[Tuple[str, int, str]]:
    all_findings = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith("project -plans")]

        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext in SCANNED_EXTENSIONS or fname in ("Dockerfile", ".env.example", "Makefile"):
                full_path = os.path.join(dirpath, fname)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    all_findings.extend(scan_text(content, os.path.relpath(full_path, root_dir)))
                except Exception as e:
                    print(f"[SCAN WARN] Could not read {full_path}: {e}", file=sys.stderr)
    return all_findings

def main():
    print(f"=== Running Canary Secret Leak Scanner on {ROOT_DIR} ===")
    findings = scan_repository(ROOT_DIR)

    self_path = os.path.relpath(__file__, ROOT_DIR)
    filtered_findings = [f for f in findings if f[0] != self_path and not f[0].endswith("test_canary_scan.py")]

    if not filtered_findings:
        print("[CANARY OK] 0 leaked secrets or hardcoded credentials detected.")
        sys.exit(0)
    else:
        print(f"[CANARY BREACH] Found {len(filtered_findings)} leaked secret instances!", file=sys.stderr)
        for path, line, desc in filtered_findings:
            print(f"  {path}:{line} -> {desc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
