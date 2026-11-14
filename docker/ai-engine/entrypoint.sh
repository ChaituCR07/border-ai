#!/usr/bin/env bash
set -euo pipefail

# Ensure cache directories exist on writable tmpfs
mkdir -p /tmp/paddle /tmp/torch /tmp/ultralytics /tmp/runtime

# Helper: read secret file into variable if defined and file exists
read_secret_file() {
  local var_name="$1"
  local file_var="${var_name}_FILE"
  if [[ -n "${!file_var:-}" && -f "${!file_var}" ]]; then
    export "${var_name}=$(cat "${!file_var}" | tr -d '\r\n')"
  fi
}

read_secret_file "DB_PASSWORD"
read_secret_file "REDIS_PASSWORD"
read_secret_file "MASTER_KEY"
read_secret_file "INTERNAL_TOKEN"

exec "$@"
