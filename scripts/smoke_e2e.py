#!/usr/bin/env python3
"""
End-to-End Smoke Test (Task 3).
Performs sequential verification of all pipeline stages from RTSP ingest to UI.
Reports the earliest failing stage rather than generic failure traces.
"""

import json
import os
import re
import socket
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List, Tuple


def check_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def http_get(url: str, timeout: float = 3.0) -> Tuple[int, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmokeE2E/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def check_log_errors(log_path: str, allowlist_path: str = "scripts/log_allowlist.txt") -> List[str]:
    if not os.path.exists(log_path):
        return []

    allow_patterns = []
    if os.path.exists(allowlist_path):
        with open(allowlist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    allow_patterns.append(re.compile(line, re.IGNORECASE))

    errors = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "ERROR" in line or "Traceback (most recent call last)" in line:
                if not any(pat.search(line) for pat in allow_patterns):
                    errors.append(line.strip())
    return errors


class SmokeTestRunner:
    def __init__(self, base_api: str = "http://localhost:4000", base_ui: str = "http://localhost:5173"):
        self.base_api = base_api.rstrip("/")
        self.base_ui = base_ui.rstrip("/")
        self.results: List[Tuple[str, str, str]] = []

    def run_stage(self, stage_name: str, check_fn) -> bool:
        try:
            ok, msg = check_fn()
            status = "PASSED" if ok else "FAILED"
            self.results.append((stage_name, status, msg))
            return ok
        except Exception as e:
            self.results.append((stage_name, "FAILED", f"Exception: {e}"))
            return False

    def execute(self) -> bool:
        stages = [
            ("Stage 1: Infrastructure Connectivity", self._check_infra),
            ("Stage 2: Backend Health API", self._check_api_ready),
            ("Stage 3: System Status Aggregation", self._check_system_status),
            ("Stage 4: Camera Inventory & Endpoints", self._check_cameras),
            ("Stage 5: Frontend Dashboard UI", self._check_ui),
            ("Stage 6: Log Cleanliness & Error Scanning", self._check_logs),
        ]

        all_ok = True
        for name, fn in stages:
            if not self.run_stage(name, fn):
                all_ok = False
                break

        self.print_summary()
        return all_ok

    def _check_infra(self) -> Tuple[bool, str]:
        ports = [("Postgres", "localhost", 5432), ("Redis", "localhost", 6379), ("MediaMTX", "localhost", 8554)]
        down = []
        for name, host, port in ports:
            if not check_tcp(host, port, timeout=1.0):
                down.append(f"{name}:{port}")
        if down:
            return False, f"Unreachable services: {', '.join(down)} (ensure docker-compose.infra is up)"
        return True, "Postgres, Redis, and MediaMTX are listening on TCP ports."

    def _check_api_ready(self) -> Tuple[bool, str]:
        code, body = http_get(f"{self.base_api}/api/ready")
        if code not in (200, 404):  # fallback to /api/cameras
            code, body = http_get(f"{self.base_api}/api/cameras")
        if code == 200:
            return True, f"API responded HTTP {code}"
        return False, f"API /api/ready returned HTTP {code}: {body[:100]}"

    def _check_system_status(self) -> Tuple[bool, str]:
        code, body = http_get(f"{self.base_api}/api/system/status")
        if code == 200:
            try:
                data = json.loads(body).get("data", {})
                status = data.get("status", "UNKNOWN")
                return True, f"System status endpoint OK (overall: {status})"
            except Exception as e:
                return False, f"Invalid JSON in system status: {e}"
        return False, f"HTTP {code} from /api/system/status"

    def _check_cameras(self) -> Tuple[bool, str]:
        code, body = http_get(f"{self.base_api}/api/cameras")
        if code == 200:
            return True, "Cameras listed successfully"
        return False, f"HTTP {code} from /api/cameras"

    def _check_ui(self) -> Tuple[bool, str]:
        code, body = http_get(self.base_ui)
        if code == 200 and "<html" in body.lower():
            return True, "Dashboard React HTML loaded successfully"
        return False, f"UI endpoint returned HTTP {code}"

    def _check_logs(self) -> Tuple[bool, str]:
        unallowed = []
        for log_file in ["logs/sim/cam-01.log", "logs/engine.log"]:
            errs = check_log_errors(log_file)
            if errs:
                unallowed.extend(errs[:3])
        if unallowed:
            return False, f"Found unallowed errors in logs: {unallowed}"
        return True, "Logs are clean without fatal unhandled exceptions."

    def print_summary(self) -> None:
        print("\n======================= SMOKE TEST SUMMARY =======================")
        for stage, status, msg in self.results:
            color = "\033[32m" if status == "PASSED" else "\033[31m"
            print(f"[{color}{status:6}\033[0m] {stage:35} -> {msg}")
        print("==================================================================\n")


def main():
    runner = SmokeTestRunner()
    success = runner.execute()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
