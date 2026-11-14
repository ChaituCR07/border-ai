#!/usr/bin/env bash
set -euo pipefail

# scripts/gen_certs.sh - Generates TLS certificates for Border-AI Nginx Edge

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERTS_DIR="${ROOT_DIR}/certs"
mkdir -p "${CERTS_DIR}"
cd "${CERTS_DIR}"

PUBLIC_HOST="${PUBLIC_HOST:-localhost}"
OPENSSL_BIN="openssl"
if [[ -x "/usr/bin/openssl" ]]; then
  OPENSSL_BIN="/usr/bin/openssl"
fi

if [[ -f "fullchain.pem" && -f "privkey.pem" && "${FORCE:-0}" != "1" ]]; then
  echo "[CERTS] TLS certificates already exist in ${CERTS_DIR} (skipping, set FORCE=1 to regenerate)"
  exit 0
fi

echo "=== Generating TLS Certificates for Nginx Edge (${PUBLIC_HOST}) ==="

if command -v mkcert >/dev/null 2>&1; then
  echo "[CERTS] mkcert detected, generating trusted local certificate..."
  mkcert -cert-file fullchain.pem -key-file privkey.pem "localhost" "127.0.0.1" "${PUBLIC_HOST}"
else
  echo "[CERTS] Generating self-signed X.509 certificate with OpenSSL..."
  
  cat > san.cnf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = US
ST = State
L = City
O = Border-AI
OU = Surveillance
CN = ${PUBLIC_HOST}

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = ${PUBLIC_HOST}
IP.1 = 127.0.0.1
EOF

  ${OPENSSL_BIN} req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -config san.cnf

  rm -f san.cnf
fi

chmod 0644 fullchain.pem
chmod 0640 privkey.pem
echo "[CERTS] Successfully generated fullchain.pem and privkey.pem in ${CERTS_DIR}"
echo "[CERTS] Note: In production environments, replace with an organization CA or Let's Encrypt certificate."
