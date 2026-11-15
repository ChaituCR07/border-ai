#!/usr/bin/env bash
# Border-AI API Authentication & Session Flow
set -euo pipefail

BASE_URL="${BORDER_API_URL:-https://localhost/api/v1}"
EMAIL="${ADMIN_EMAIL:-admin@border.local}"
PASSWORD="${ADMIN_PASSWORD:-$(cat secrets/bootstrap_admin_password 2>/dev/null || echo 'BorderAdmin2026!')}"

echo "=== 1. Authenticating as Administrator ==="
LOGIN_RES=$(curl -sk -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")

ACCESS_TOKEN=$(echo "${LOGIN_RES}" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log(JSON.parse(d).data?.accessToken||JSON.parse(d).token||''))")

if [[ -z "${ACCESS_TOKEN}" ]]; then
  echo "[ERROR] Authentication failed: ${LOGIN_RES}"
  exit 1
fi
echo "[OK] Successfully authenticated. Acquired Bearer token."

echo "=== 2. Accessing Protected Camera List ==="
curl -sk -X GET "${BASE_URL}/cameras" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log('Registered cameras:', JSON.parse(d).data?.length || 0))"

echo "=== 3. Checking System Status ==="
curl -sk -X GET "${BASE_URL}/system/status" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
echo ""
