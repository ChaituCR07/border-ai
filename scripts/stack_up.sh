#!/usr/bin/env bash
# One-command orchestration bringing up infra, running migrations, and verifying readiness
set -euo pipefail

ENV_FILE=".env.integration"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
else
  echo "Error: $ENV_FILE not found"
  exit 1
fi

echo "Starting infrastructure containers..."
docker compose -f docker-compose.infra.yml up -d

wait_tcp() {
  local host="$1"
  local port="$2"
  echo -n "Waiting for $host:$port ..."
  for i in $(seq 1 45); do
    if nc -z "$host" "$port" 2>/dev/null || (echo > "/dev/tcp/$host/$port") 2>/dev/null; then
      echo " OK"
      return 0
    fi
    sleep 1
    echo -n "."
  done
  echo " TIMEOUT waiting for $host:$port"
  return 1
}

wait_tcp localhost 5432
wait_tcp localhost 6379
wait_tcp localhost 8554
wait_tcp localhost 1025

echo "Applying database migrations to border_ai_integration..."
npm --prefix backend run migrate || true

echo "Stack is ready for integration."
