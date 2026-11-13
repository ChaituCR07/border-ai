import base64
import json
import os
import subprocess
from typing import Dict, Any, Optional

class VaultDecryptionError(Exception):
    """Raised when vault decryption or authentication tag validation fails."""
    pass

def _decrypt_via_node(camera_id: str, envelope: Dict[str, Any], master_key_hex: str) -> str:
    script = """
const crypto = require('crypto');
const args = JSON.parse(process.argv[1]);
const key = Buffer.from(args.keyHex, 'hex');
const nonce = Buffer.from(args.envelope.nonce, 'base64');
const ct = Buffer.from(args.envelope.ct, 'base64');
const tag = Buffer.from(args.envelope.tag, 'base64');

try {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, nonce);
  decipher.setAAD(Buffer.from(args.cameraId, 'utf8'));
  decipher.setAuthTag(tag);
  const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
  process.stdout.write(pt.toString('utf8'));
} catch (e) {
  process.stderr.write('AUTH_FAILED');
  process.exit(2);
}
"""
    payload = json.dumps({
        "keyHex": master_key_hex,
        "cameraId": camera_id,
        "envelope": envelope
    })
    
    proc = subprocess.run(
        ["node", "-e", script, payload],
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        raise VaultDecryptionError("Authentication tag validation failed or ciphertext corrupted")
    return proc.stdout

def open_credential(camera_id: str, envelope: Dict[str, Any], master_key: bytes) -> str:
    """
    Decrypts AES-256-GCM camera credential envelope with camera_id as AAD.
    """
    if not camera_id:
        raise ValueError("camera_id is required as AAD")
    if not isinstance(envelope, dict) or not all(k in envelope for k in ("nonce", "ct", "tag")):
        raise ValueError("Invalid envelope structure: missing nonce, ct, or tag")

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(master_key)
        nonce = base64.b64decode(envelope["nonce"])
        ct_and_tag = base64.b64decode(envelope["ct"]) + base64.b64decode(envelope["tag"])
        aad = camera_id.encode("utf-8")
        decrypted = aesgcm.decrypt(nonce, ct_and_tag, aad)
        return decrypted.decode("utf-8")
    except ImportError:
        return _decrypt_via_node(camera_id, envelope, master_key.hex())
    except Exception as e:
        raise VaultDecryptionError(f"Vault decryption failed: {e}") from e
