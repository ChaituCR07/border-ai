#!/usr/bin/env bash
# Terminate any lingering ffmpeg cctv_sim or test processes cleanly
set -euo pipefail

echo "Checking for lingering integration processes..."

# Match ffmpeg streaming to mediamtx
pkill -f "ffmpeg.*mediamtx" || true
pkill -f "cctv_sim.py" || true

# Give time to terminate cleanly
sleep 0.5

echo "Cleaned up straggler processes."
