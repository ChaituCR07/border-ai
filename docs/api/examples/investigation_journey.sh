#!/usr/bin/env bash
# Border-AI Vehicle Journey Reconstruction & CSV Export Flow
set -euo pipefail

BASE_URL="${BORDER_API_URL:-https://localhost/api/v1}"
TOKEN="${1:-${ACCESS_TOKEN:-}}"
PLATE="${2:-KA01AB1234}"

if [[ -z "${TOKEN}" ]]; then
  echo "Usage: $0 <BEARER_TOKEN> [LICENSE_PLATE]"
  exit 1
fi

echo "=== 1. Searching Vehicle Sightings for Plate: ${PLATE} (Look-alike Mode) ==="
curl -sk -X GET "${BASE_URL}/investigation/search?plate=${PLATE}&lookalike=true&limit=10" \
  -H "Authorization: Bearer ${TOKEN}"

echo "=== 2. Reconstructing Cross-Camera Journey Graph ==="
curl -sk -X GET "${BASE_URL}/investigation/journey?plate=${PLATE}" \
  -H "Authorization: Bearer ${TOKEN}"

echo "=== 3. Exporting Audit & Sighting History to CSV ==="
curl -sk -X GET "${BASE_URL}/export/csv?entity=vehicle&query=${PLATE}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -o "journey_${PLATE}.csv"

echo "[OK] Exported forensic journey to journey_${PLATE}.csv"
