#!/usr/bin/env bash
set -euo pipefail

# scripts/gen_secrets.sh - Generates cryptographically secure deployment secrets and Redis ACL

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${ROOT_DIR}/secrets"
mkdir -p "${SECRETS_DIR}"
cd "${SECRETS_DIR}"
umask 077

rand_base64() {
  if command -v node >/dev/null 2>&1; then
    node -e "process.stdout.write(require('crypto').randomBytes(27).toString('base64'))"
  elif [[ -x "/usr/bin/openssl" ]]; then
    /usr/bin/openssl rand -base64 36 | tr -d '\r\n'
  else
    openssl rand -base64 36 | tr -d '\r\n'
  fi
}

gen_secret() {
  local name="$1"
  if [[ -f "${name}" && "${FORCE:-0}" != "1" ]]; then
    echo "[SECRETS] ${name} already exists (skipping, set FORCE=1 to overwrite)"
  else
    rand_base64 > "${name}"
    echo "[SECRETS] Created ${name}"
  fi
}

echo "=== Generating Border-AI Deployment Secrets ==="

# 1. PostgreSQL Database Passwords
for p in pg_admin_password pg_api_password pg_engine_password pg_sink_password pg_retention_password; do
  gen_secret "$p"
done

# 2. Redis Passwords
for r in redis_engine_password redis_sink_password redis_gateway_password redis_api_password redis_healthcheck_password; do
  gen_secret "$r"
done

# 3. Application Security Secrets
for s in password_pepper internal_token mediamtx_publish_password mediamtx_read_password smtp_password; do
  gen_secret "$s"
done

# 4. Master Vault Key (32 bytes hex = 64 characters)
if [[ -f "master_key" && "${FORCE:-0}" != "1" ]]; then
  echo "[SECRETS] master_key already exists (skipping)"
else
  if command -v node >/dev/null 2>&1; then
    node -e "process.stdout.write(require('crypto').randomBytes(32).toString('hex'))" > master_key
  elif [[ -x "/usr/bin/openssl" ]]; then
    /usr/bin/openssl rand -hex 32 | tr -d '\r\n' > master_key
  else
    openssl rand -hex 32 | tr -d '\r\n' > master_key
  fi
  echo "[SECRETS] Created master_key"
fi

# 5. Ed25519 JWT Signing Key
if [[ -f "jwt_private_key" && "${FORCE:-0}" != "1" ]]; then
  echo "[SECRETS] jwt_private_key already exists (skipping)"
else
  node -e "
    const crypto = require('crypto');
    const { privateKey } = crypto.generateKeyPairSync('ed25519', {
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
    });
    process.stdout.write(privateKey);
  " > jwt_private_key
  echo "[SECRETS] Created jwt_private_key"
fi

# 6. Bootstrap Administrator Password
if [[ -f "bootstrap_admin_password" && "${FORCE:-0}" != "1" ]]; then
  echo "[SECRETS] bootstrap_admin_password already exists (skipping)"
else
  rand_base64 > bootstrap_admin_password
  echo "[SECRETS] Created bootstrap_admin_password (save for initial root login)"
fi

# 7. Generate Redis users.acl with SHA-256 Hashed Passwords
hash_redis_password() {
  local user="$1"
  local pass
  pass="$(cat "redis_${user}_password" | tr -d '\r\n')"
  if command -v node >/dev/null 2>&1; then
    node -e "process.stdout.write(require('crypto').createHash('sha256').update(process.argv[1]).digest('hex'))" "$pass"
  elif command -v sha256sum >/dev/null 2>&1; then
    printf "%s" "$pass" | sha256sum | cut -d' ' -f1
  else
    printf "%s" "$pass" | shasum -a 256 | cut -d' ' -f1
  fi
}

ENGINE_HASH="$(hash_redis_password engine)"
SINK_HASH="$(hash_redis_password sink)"
GATEWAY_HASH="$(hash_redis_password gateway)"
API_HASH="$(hash_redis_password api)"
HEALTH_HASH="$(hash_redis_password healthcheck)"

cat > users.acl <<EOF
user default off
user engine      on #${ENGINE_HASH} ~surveillance.* ~camera:status:* ~engine:status +xadd +set +ping
user sink        on #${SINK_HASH} ~surveillance.* +xreadgroup +xack +xclaim +xautoclaim +xpending +xadd +xgroup +xinfo +ping
user gateway     on #${GATEWAY_HASH} ~surveillance.alerts +xread +ping
user api         on #${API_HASH} ~camera:status:* ~engine:status ~surveillance.* +get +mget +xinfo +xlen +ping
user healthcheck on #${HEALTH_HASH} +ping
EOF
echo "[SECRETS] Created users.acl (Redis ACL with SHA-256 password digests)"

# Set permissions so UID 10001 (container user) can read them
chmod 0644 "${SECRETS_DIR}"/*
chmod 0755 "${SECRETS_DIR}"
echo "=== Secrets generation complete ==="
