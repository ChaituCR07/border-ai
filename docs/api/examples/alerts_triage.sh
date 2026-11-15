#!/usr/bin/env bash
# Border-AI Alert Listing & Operator Acknowledgement Flow
set -euo pipefail

BASE_URL="${BORDER_API_URL:-https://localhost/api/v1}"
TOKEN="${1:-${ACCESS_TOKEN:-}}"

if [[ -z "${TOKEN}" ]]; then
  echo "Usage: $0 <BEARER_TOKEN>"
  exit 1
fi

echo "=== 1. Fetching Open Alerts (Keyset Paginated) ==="
ALERTS_RES=$(curl -sk -X GET "${BASE_URL}/alerts?status=OPEN&limit=5" \
  -H "Authorization: Bearer ${TOKEN}")

FIRST_ALERT_ID=$(echo "${ALERTS_RES}" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log(JSON.parse(d).data?.[0]?.id || ''))")

if [[ -z "${FIRST_ALERT_ID}" ]]; then
  echo "[INFO] No OPEN alerts currently in database queue."
  exit 0
fi

echo "[OK] Found open alert ID: ${FIRST_ALERT_ID}"

echo "=== 2. Acknowledging Alert ${FIRST_ALERT_ID} ==="
ACK_RES=$(curl -sk -X PATCH "${BASE_URL}/alerts/${FIRST_ALERT_ID}/acknowledge" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"note": "Triage verified by perimeter operator; patrol dispatched"}')

echo "[OK] Acknowledgement Response:"
echo "${ACK_RES}"
