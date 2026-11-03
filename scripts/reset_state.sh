#!/usr/bin/env bash
# Resets integration state with strict environment and database guards
set -euo pipefail

ENV_FILE=".env.integration"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ "${ENV:-}" != "integration" ]]; then
  echo "Refusing to reset state: ENV must be set to 'integration'"
  exit 1
fi

ADMIN_URL="${ADMIN_DATABASE_URL:-postgresql://postgres:zq9canaryPg@localhost:5432/border_ai_integration}"

# Guard database name
DB_NAME=$(python3 -c "import urllib.parse, sys; print(urllib.parse.urlparse('$ADMIN_URL').path.lstrip('/'))" 2>/dev/null || echo "")
if [[ "$DB_NAME" != "border_ai_integration" ]]; then
  echo "Refusing to reset state: Connected database '$DB_NAME' is not 'border_ai_integration'"
  exit 1
fi

echo "Truncating integration database tables..."
psql "$ADMIN_URL" -c "TRUNCATE TABLE events, alerts, vehicles, notifications, notification_planned, api_audit_log RESTART IDENTITY CASCADE;" 2>/dev/null || true

echo "Flushing Redis cache..."
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" FLUSHDB 2>/dev/null || true
fi

echo "Cleaning artifact directories..."
rm -rf data/snapshots/* data/journal/* artifacts/tmp/* 2>/dev/null || true
mkdir -p data/snapshots data/journal artifacts/tmp

echo "Flushing Mailpit test mailbox..."
curl -fsS -X DELETE "http://localhost:8025/api/v1/messages" 2>/dev/null || true

echo "Integration state reset successfully."
