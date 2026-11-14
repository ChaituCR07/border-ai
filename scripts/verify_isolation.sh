#!/usr/bin/env bash
set -euo pipefail

# scripts/verify_isolation.sh - Audits network isolation & port publication boundaries

echo "=== Verifying Border-AI Network Segmentation & Port Isolation ==="

PASS_COUNT=0
FAIL_COUNT=0

check() {
  local desc="$1"
  local cond="$2"
  if eval "$cond"; then
    echo "  [PASS] $desc"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  [FAIL] $desc"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# 1. Static Compose Network Audit
check "Data network marked internal: true" \
  "grep -A 2 'data:' docker-compose.yml | grep -q 'internal: true'"

check "App network marked internal: true" \
  "grep -A 2 'app:' docker-compose.yml | grep -q 'internal: true'"

check "Media network marked internal: true" \
  "grep -A 2 'media:' docker-compose.yml | grep -q 'internal: true'"

check "Only Nginx publishes host ports in production compose" \
  "[[ \$(grep -c '^[[:space:]]*ports:' docker-compose.yml) -eq 1 ]]"

check "PostgreSQL publishes NO ports in production configuration" \
  "! sed -n '/^  postgres:/,/^  [a-zA-Z0-9_-]*:/p' docker-compose.yml | grep -q 'ports:'"

check "Redis publishes NO ports in production configuration" \
  "! sed -n '/^  redis:/,/^  [a-zA-Z0-9_-]*:/p' docker-compose.yml | grep -q 'ports:'"

check "AI Engine publishes NO ports in production configuration" \
  "! sed -n '/^  ai-engine:/,/^  [a-zA-Z0-9_-]*:/p' docker-compose.yml | grep -q 'ports:'"

# 2. Dynamic Port Audit (if running under Docker)
if docker info >/dev/null 2>&1; then
  CONTAINERS=$(docker compose ps -q 2>/dev/null || true)
  if [[ -n "${CONTAINERS}" ]]; then
    for cid in ${CONTAINERS}; do
      CNAME=$(docker inspect --format '{{.Name}}' "${cid}" | sed 's/^\///')
      if [[ "${CNAME}" != *"nginx"* ]]; then
        PORTS=$(docker inspect --format '{{json .NetworkSettings.Ports}}' "${cid}")
        check "${CNAME}: publishes no host ports" \
          "[[ \"${PORTS}\" == \"null\" || \"${PORTS}\" == \"{}\" || ! \"${PORTS}\" =~ HostPort ]]"
      fi
    done
  fi
fi

echo "=== Network Isolation Summary: ${PASS_COUNT} Passed, ${FAIL_COUNT} Failed ==="
[[ ${FAIL_COUNT} -eq 0 ]]
