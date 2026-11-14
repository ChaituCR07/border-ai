#!/usr/bin/env python3
"""
CCTV Simulation Supervisor for Docker Compose
Streams simulated camera feeds into MediaMTX in demo and test profiles.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import List

CHILD_PROCS: List[subprocess.Popen] = []

def signal_handler(signum, frame):
    print(f"[CCTV-SIM] Received signal {signum}, stopping child streams...", flush=True)
    for p in CHILD_PROCS:
        if p.poll() is None:
            p.terminate()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def get_publish_password() -> str:
    secret_path = "/run/secrets/mediamtx_publish_password"
    if os.path.exists(secret_path):
        with open(secret_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("MEDIAMTX_PUBLISH_PASSWORD", "publishpass2026")

def main():
    parser = argparse.ArgumentParser(description="Docker CCTV Simulator Supervisor")
    parser.add_argument("--scenario", default=os.environ.get("SCENARIO", "demo"), help="Scenario name")
    parser.add_argument("--host", default=os.environ.get("MEDIAMTX_HOST", "mediamtx"), help="MediaMTX hostname")
    parser.add_argument("--port", default=int(os.environ.get("MEDIAMTX_PORT", "8554")), type=int, help="RTSP port")
    args = parser.parse_args()

    password = get_publish_password()
    print(f"[CCTV-SIM] Starting camera simulation for scenario '{args.scenario}' targeting rtsp://{args.host}:{args.port}...", flush=True)

    # In synthetic container environments where footage files may not exist, generate test video patterns
    cameras = ["cam1", "cam2"]
    for cam in cameras:
        rtsp_target = f"rtsp://publisher:{password}@{args.host}:{args.port}/{cam}"
        cmd = [
            "ffmpeg",
            "-re",
            "-f", "lavfi",
            "-i", f"testsrc=size=1280x720:rate=15",
            "-vf", f"drawtext=text='{cam.upper()} Simulated %{{localtime}}':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.6:x=20:y=20",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-f", "rtsp",
            "-rtsp_transport", "tcp",
            rtsp_target,
        ]
        
        print(f"[CCTV-SIM] Spawning feed for {cam}...", flush=True)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            CHILD_PROCS.append(proc)
        except Exception as e:
            print(f"[CCTV-SIM ERROR] Failed to start feed for {cam}: {e}", file=sys.stderr)

    while True:
        time.sleep(5)
        for i, p in enumerate(CHILD_PROCS):
            if p.poll() is not None:
                print(f"[CCTV-SIM WARN] Camera feed {i} exited with code {p.returncode}", flush=True)

if __name__ == "__main__":
    main()
