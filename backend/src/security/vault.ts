import crypto from 'node:crypto';

export interface VaultEnvelope {
  key_id: string;
  nonce: string; // Base64 encoded 12-byte IV
  ct: string;    // Base64 encoded ciphertext
  tag: string;   // Base64 encoded 16-byte authentication tag
}

export const DEFAULT_KEY_ID = 'vault-2026-v1';

let cachedMasterKey: Buffer | null = null;

/**
 * Retrieves the 32-byte AES-256-GCM master vault key
 */
export function getVaultMasterKey(): Buffer {
  if (cachedMasterKey) {
    return cachedMasterKey;
  }

  const envKey = process.env.VAULT_MASTER_KEY;
  if (envKey) {
    if (envKey.length === 64) {
      cachedMasterKey = Buffer.from(envKey, 'hex');
    } else {
      cachedMasterKey = Buffer.from(envKey, 'base64');
    }
    if (cachedMasterKey.length !== 32) {
      throw new Error(`VAULT_MASTER_KEY must be exactly 32 bytes (got ${cachedMasterKey.length})`);
    }
    return cachedMasterKey;
  }

  // Development/Test fallback with warning
  console.warn('[VAULT WARNING] VAULT_MASTER_KEY not set. Using ephemeral dev key.');
  cachedMasterKey = crypto.createHash('sha256').update('border-ai-dev-vault-secret-key-salt').digest();
  return cachedMasterKey;
}

export function setVaultMasterKeyForTest(key: Buffer | null): void {
  cachedMasterKey = key;
}

/**
 * Seals plaintext camera credentials into an AES-256-GCM envelope
 * Authenticated Additional Data (AAD) is strictly bound to `cameraId`.
 */
export function sealCredential(
  cameraId: string,
  plaintext: string,
  opts?: { key?: Buffer; nonce?: Buffer; keyId?: string }
): VaultEnvelope {
  if (!cameraId) {
    throw new Error('cameraId is required as Authenticated Additional Data (AAD)');
  }

  const key = opts?.key ?? getVaultMasterKey();
  const nonce = opts?.nonce ?? crypto.randomBytes(12);
  const keyId = opts?.keyId ?? DEFAULT_KEY_ID;

  const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
  cipher.setAAD(Buffer.from(cameraId, 'utf8'));

  const ct = Buffer.concat([
    cipher.update(Buffer.from(plaintext, 'utf8')),
    cipher.final(),
  ]);

  const tag = cipher.getAuthTag();

  return {
    key_id: keyId,
    nonce: nonce.toString('base64'),
    ct: ct.toString('base64'),
    tag: tag.toString('base64'),
  };
}

/**
 * Opens and decrypts an AES-256-GCM envelope
 * Throws if AAD (cameraId), ciphertext, or auth tag does not verify.
 */
export function openCredential(
  cameraId: string,
  envelope: VaultEnvelope,
  customKey?: Buffer
): string {
  if (!cameraId) {
    throw new Error('cameraId is required for AAD verification');
  }

  const key = customKey ?? getVaultMasterKey();
  const nonce = Buffer.from(envelope.nonce, 'base64');
  const ct = Buffer.from(envelope.ct, 'base64');
  const tag = Buffer.from(envelope.tag, 'base64');

  if (nonce.length !== 12) {
    throw new Error(`Invalid nonce length: expected 12 bytes, got ${nonce.length}`);
  }
  if (tag.length !== 16) {
    throw new Error(`Invalid auth tag length: expected 16 bytes, got ${tag.length}`);
  }

  const decipher = crypto.createDecipheriv('aes-256-gcm', key, nonce);
  decipher.setAAD(Buffer.from(cameraId, 'utf8'));
  decipher.setAuthTag(tag);

  try {
    const pt = Buffer.concat([
      decipher.update(ct),
      decipher.final(),
    ]);
    return pt.toString('utf8');
  } catch (err) {
    throw new Error(`Vault authentication or decryption failed: Invalid ciphertext, tag, or camera ID mismatch`);
  }
}
