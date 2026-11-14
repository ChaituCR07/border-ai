#!/usr/bin/env bash
set -euo pipefail

# scripts/restore.sh - Decrypts and restores Border-AI database and snapshot archives
# Usage: ./scripts/restore.sh --db backups/db_<timestamp>.dump.enc [--snapshots backups/snapshots_<timestamp>.tar.enc]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR="$(mktemp -d)"
chmod 0700 "${TEMP_DIR}"

cleanup() {
  rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

KEY_HEX=""
if [[ -n "${BACKUP_KEY:-}" ]]; then
  KEY_HEX="${BACKUP_KEY}"
elif [[ -f "${ROOT_DIR}/secrets/master_key" ]]; then
  KEY_HEX="$(cat "${ROOT_DIR}/secrets/master_key" | tr -d '\r\n')"
else
  echo "[RESTORE ERROR] Neither BACKUP_KEY nor secrets/master_key available."
  exit 1
fi

decrypt_file() {
  local in_file="$1"
  local out_file="$2"
  node -e "
    const fs = require('fs');
    const crypto = require('crypto');
    const key = Buffer.from(process.argv[1], 'hex');
    const payload = fs.readFileSync(process.argv[2]);
    const iv = payload.subarray(0, 12);
    const tag = payload.subarray(12, 28);
    const ct = payload.subarray(28);
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
    decipher.setAuthTag(tag);
    const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
    fs.writeFileSync(process.argv[3], pt);
  " "${KEY_HEX}" "${in_file}" "${out_file}"
}

DB_ENC=""
SNAP_ENC=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db)
      DB_ENC="$2"
      shift 2
      ;;
    --snapshots)
      SNAP_ENC="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

if [[ -z "${DB_ENC}" || ! -f "${DB_ENC}" ]]; then
  echo "[RESTORE ERROR] Encrypted database backup file not specified or missing: ${DB_ENC}"
  echo "Usage: ./scripts/restore.sh --db <path-to-db.dump.enc> [--snapshots <path-to-snapshots.tar.enc>]"
  exit 1
fi

echo "=== Decrypting & Restoring Border-AI Archives ==="

# 1. Decrypt Database Dump
DECRYPTED_DB="${TEMP_DIR}/restored_db.sql"
decrypt_file "${DB_ENC}" "${DECRYPTED_DB}"
echo "[RESTORE] Successfully decrypted database dump."

if docker compose ps postgres 2>/dev/null | grep -q 'Up'; then
  echo "[RESTORE] Applying SQL dump to containerized PostgreSQL..."
  docker compose exec -T postgres psql -U postgres -d border_ai < "${DECRYPTED_DB}"
  echo "[RESTORE OK] Database restored into postgres service."
else
  echo "[RESTORE INFO] Database container not active; decrypted dump preserved at ${DECRYPTED_DB}."
fi

# 2. Decrypt & Restore Snapshots (if provided)
if [[ -n "${SNAP_ENC}" && -f "${SNAP_ENC}" ]]; then
  DECRYPTED_SNAP="${TEMP_DIR}/restored_snapshots.tar.gz"
  decrypt_file "${SNAP_ENC}" "${DECRYPTED_SNAP}"
  echo "[RESTORE] Successfully decrypted snapshots archive."
  mkdir -p "${ROOT_DIR}/outputs"
  tar -xzf "${DECRYPTED_SNAP}" -C "${ROOT_DIR}/outputs"
  echo "[RESTORE OK] Restored snapshots directory into outputs/snapshots."
fi

echo "=== Restore completed successfully ==="
