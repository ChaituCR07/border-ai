#!/usr/bin/env bash
# Verifies system health across all integration components
set -uo pipefail

ALL_OK=true

check_component() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    printf "  %-20s [ \033[32mOK\033[0m ]\n" "$name"
  else
    printf "  %-20s [ \033[31mFAIL\033[0m ]\n" "$name"
    ALL_OK=false
  fi
}

echo "=== System Health Inspection ==="
check_component "PostgreSQL (5432)" "nc -z localhost 5432 || (echo > /dev/tcp/localhost/5432)"
check_component "Redis (6379)" "nc -z localhost 6379 || (echo > /dev/tcp/localhost/6379)"
check_component "MediaMTX RTSP (8554)" "nc -z localhost 8554 || (echo > /dev/tcp/localhost/8554)"
check_component "Mailpit SMTP (1025)" "nc -z localhost 1025 || (echo > /dev/tcp/localhost/1025)"
check_component "Mailpit Web (8025)" "curl -s -f http://localhost:8025/api/v1/messages"
check_component "Backend API (4000)" "curl -s -f http://localhost:4000/api/ready || curl -s -f http://localhost:4000/api/health"

if [[ "$ALL_OK" = true ]]; then
  echo "All inspected components are reachable."
  exit 0
else
  echo "One or more components are down."
  exit 1
fi
