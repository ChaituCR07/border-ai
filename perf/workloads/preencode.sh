#!/usr/bin/env bash
# Pre-encode raw test footage to standardized H.264 streams
# Flag parameters: -g 25 (fixed 1-second GOP), -bf 0 (no B-frames), constant 25 FPS.
# This ensures RTSP simulator streaming runs with `-c copy`, consuming < 1% CPU.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

FOOTAGE_DIR="${REPO_ROOT}/footage"
OUTPUT_DIR="${REPO_ROOT}/perf/workloads/encoded"

mkdir -p "${OUTPUT_DIR}"

echo "[*] Pre-encoding workload clips for low-overhead benchmark streaming..."

find "${FOOTAGE_DIR}" -type f -name "*.mp4" | while read -r clip; do
    rel_path="${clip#"${FOOTAGE_DIR}/"}"
    out_file="${OUTPUT_DIR}/${rel_path//\//_}"

    echo "    Encoding: ${rel_path} -> ${out_file}"
    if command -v ffmpeg &>/dev/null; then
        ffmpeg -y -i "${clip}" \
            -c:v libx264 -preset fast -crf 22 \
            -pix_fmt yuv420p -r 25 -g 25 -bf 0 \
            -an "${out_file}" -loglevel warning || true
    else
        echo "    [WARN] ffmpeg not installed; copying reference file"
        cp "${clip}" "${out_file}" 2>/dev/null || true
    fi
done

echo "[OK] Workload pre-encoding complete."
