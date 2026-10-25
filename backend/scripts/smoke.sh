#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:4000}"
echo "Running smoke tests against ${BASE_URL}..."

check_status() {
  local method="$1"
  local url="$2"
  local expected_status="$3"
  local data="${4:-}"
  local headers="${5:-}"

  if [ -n "$data" ]; then
    status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${url}" \
      -H "Content-Type: application/json" ${headers:+-H "$headers"} -d "$data")
  else
    status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${url}" \
      ${headers:+-H "$headers"})
  fi

  if [ "$status" -eq "$expected_status" ]; then
    echo "  [PASS] $method $url -> $status"
  else
    echo "  [FAIL] $method $url -> expected $expected_status, got $status"
    exit 1
  fi
}

echo "1. Health & Documentation"
check_status "GET" "/api/health" 200
check_status "GET" "/api/ready" 200
check_status "GET" "/docs" 200
check_status "GET" "/openapi.json" 200

echo "2. Cameras"
check_status "GET" "/api/cameras" 200
check_status "POST" "/api/cameras" 201 '{"camera_id":"SMOKE-01","name":"Smoke Test Cam","enabled":true}'
check_status "GET" "/api/cameras/SMOKE-01" 200
check_status "PUT" "/api/cameras/SMOKE-01" 200 '{"name":"Smoke Cam Updated","enabled":true}'

echo "3. Events & Keyset Pagination"
check_status "GET" "/api/events?limit=10" 200
check_status "GET" "/api/events?severity=CRITICAL" 200

echo "4. Alerts"
check_status "GET" "/api/alerts?limit=10" 200

echo "5. Watchlist"
check_status "GET" "/api/watchlist" 200
check_status "POST" "/api/watchlist" 201 '{"entity_type":"VEHICLE","identifier":"ka-01 ab 9988","name":"Smoke Vehicle","risk_level":"HIGH"}'

echo "6. Analytics"
check_status "GET" "/api/analytics/events?bucket=hour" 200
check_status "GET" "/api/analytics/cameras" 200
check_status "GET" "/api/analytics/threats" 200

echo "7. Security & Error Handling"
check_status "POST" "/api/cameras" 400 '{"camera_id":"SMOKE-LEAK","name":"Leaky","stream_url":"rtsp://user:pass@10.0.0.1/live"}'
check_status "GET" "/api/cameras/NONEXISTENT_CAMERA_ID" 404
check_status "GET" "/api/events?limit=0" 400
check_status "GET" "/api/snapshots/../../etc/passwd" 404

echo "ALL SMOKE TESTS PASSED!"
