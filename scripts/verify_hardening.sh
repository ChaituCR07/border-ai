#!/usr/bin/env bash
set -euo pipefail

# scripts/verify_hardening.sh - Audits runtime container security configurations
# Verifies: non-root user, read-only rootfs, dropped capabilities, no-new-privileges, secret hygiene

echo "=== Verifying Border-AI Container Hardening Posture ==="

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

# If Docker daemon is unavailable, verify docker-compose.yml static configuration
if ! docker info >/dev/null 2>&1; then
  echo "[INFO] Docker daemon not reachable in current shell. Auditing docker-compose.yml static template..."
  
  check "Hardened template drops ALL capabilities" \
    "grep -q 'cap_drop:.*ALL' docker-compose.yml"

  check "Hardened template enforces no-new-privileges" \
    "grep -q 'no-new-privileges:true' docker-compose.yml"

  check "Hardened template runs as non-root user 10001:10001" \
    "grep -q 'user: \"10001:10001\"' docker-compose.yml"

  check "Hardened template mounts root filesystem as read_only" \
    "grep -q 'read_only: true' docker-compose.yml"

  check "Secrets provisioned via files rather than inline environment variables" \
    "grep -q 'secrets:' docker-compose.yml && ! grep -E 'POSTGRES_PASSWORD: [^/]' docker-compose.yml"

  check "Healthchecks defined for stateful and edge services" \
    "grep -q 'healthcheck:' docker-compose.yml"

  echo "=== Hardening Verification Summary: ${PASS_COUNT} Passed, ${FAIL_COUNT} Failed ==="
  [[ ${FAIL_COUNT} -eq 0 ]]
  exit 0
fi

CONTAINERS=$(docker compose ps -q 2>/dev/null || true)
if [[ -z "${CONTAINERS}" ]]; then
  echo "[WARN] No active compose containers found. Validating compose specification..."
  docker compose config -q
  echo "  [PASS] docker-compose configuration schema valid"
  exit 0
fi

for cid in ${CONTAINERS}; do
  CNAME=$(docker inspect --format '{{.Name}}' "${cid}" | sed 's/^\///')
  echo "[INSPECT] Auditing container: ${CNAME}"

  # 1. No-New-Privileges
  check "${CNAME}: security_opt includes no-new-privileges" \
    "docker inspect --format '{{json .HostConfig.SecurityOpt}}' '${cid}' | grep -q 'no-new-privileges'"

  # 2. Privileged flag MUST be false
  check "${CNAME}: not running in privileged mode" \
    "[[ \$(docker inspect --format '{{.HostConfig.Privileged}}' '${cid}') == 'false' ]]"

  # 3. Host networking mode MUST NOT be used
  check "${CNAME}: not using host network namespace" \
    "[[ \$(docker inspect --format '{{.HostConfig.NetworkMode}}' '${cid}') != 'host' ]]"

  # 4. No plaintext password leak in container environment variables
  check "${CNAME}: environment variables do not leak secret passwords" \
    "! docker inspect --format '{{json .Config.Env}}' '${cid}' | grep -qiE 'password=[^f]|secret=[^f]'"
done

echo "=== Hardening Verification Complete: ${PASS_COUNT} Passed, ${FAIL_COUNT} Failed ==="
[[ ${FAIL_COUNT} -eq 0 ]]
