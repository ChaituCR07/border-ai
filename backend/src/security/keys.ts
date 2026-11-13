import crypto from 'node:crypto';
import fs from 'node:fs';

export interface Ed25519Jwk {
  kty: 'OKP';
  crv: 'Ed25519';
  x: string;
  kid: string;
  use: 'sig';
  alg: 'EdDSA';
}

export interface KeyPairInfo {
  kid: string;
  privateKeyPem: string;
  publicKeyPem: string;
  jwk: Ed25519Jwk;
  privateKey: crypto.KeyObject;
  publicKey: crypto.KeyObject;
}

export interface JwksResponse {
  keys: Ed25519Jwk[];
}

/**
 * Derive kid as base64url(sha256(publicKeySpkiDer))[:16]
 */
export function deriveKeyId(publicKey: crypto.KeyObject): string {
  const der = publicKey.export({ type: 'spki', format: 'der' });
  return crypto.createHash('sha256').update(der).digest('base64url').slice(0, 16);
}

/**
 * Generate a fresh Ed25519 key pair with its derived kid and JWK representation
 */
export function generateEd25519KeyPair(): KeyPairInfo {
  const { privateKey, publicKey } = crypto.generateKeyPairSync('ed25519');
  const kid = deriveKeyId(publicKey);
  const privateKeyPem = privateKey.export({ type: 'pkcs8', format: 'pem' }) as string;
  const publicKeyPem = publicKey.export({ type: 'spki', format: 'pem' }) as string;
  const rawJwk = publicKey.export({ format: 'jwk' }) as { kty: string; crv: string; x: string };

  const jwk: Ed25519Jwk = {
    kty: 'OKP',
    crv: 'Ed25519',
    x: rawJwk.x,
    kid,
    use: 'sig',
    alg: 'EdDSA',
  };

  return {
    kid,
    privateKeyPem,
    publicKeyPem,
    jwk,
    privateKey,
    publicKey,
  };
}

class KeyManager {
  private activeKeyPair: KeyPairInfo | null = null;
  private previousKeys: Map<string, crypto.KeyObject> = new Map();
  private previousJwks: Map<string, Ed25519Jwk> = new Map();

  constructor() {
    this.init();
  }

  private init() {
    // 1. Try to load private key from env or file
    let privKeyPem = process.env.JWT_PRIVATE_KEY;
    if (!privKeyPem && process.env.JWT_PRIVATE_KEY_FILE) {
      try {
        if (fs.existsSync(process.env.JWT_PRIVATE_KEY_FILE)) {
          privKeyPem = fs.readFileSync(process.env.JWT_PRIVATE_KEY_FILE, 'utf-8');
        }
      } catch (err: any) {
        console.warn(`[keys] Failed to read JWT_PRIVATE_KEY_FILE: ${err.message}`);
      }
    }

    if (privKeyPem && privKeyPem.includes('BEGIN PRIVATE KEY')) {
      try {
        const privateKey = crypto.createPrivateKey({ key: privKeyPem, format: 'pem', type: 'pkcs8' });
        const publicKey = crypto.createPublicKey(privateKey);
        const kid = process.env.JWT_KID || deriveKeyId(publicKey);
        const publicKeyPem = publicKey.export({ type: 'spki', format: 'pem' }) as string;
        const rawJwk = publicKey.export({ format: 'jwk' }) as { kty: string; crv: string; x: string };
        const jwk: Ed25519Jwk = {
          kty: 'OKP',
          crv: 'Ed25519',
          x: rawJwk.x,
          kid,
          use: 'sig',
          alg: 'EdDSA',
        };

        this.activeKeyPair = {
          kid,
          privateKeyPem: privKeyPem,
          publicKeyPem,
          jwk,
          privateKey,
          publicKey,
        };
      } catch (err: any) {
        console.error(`[keys] Invalid private key configured: ${err.message}`);
      }
    }

    // Fallback: Generate ephemeral key pair for development/tests
    if (!this.activeKeyPair) {
      if (process.env.NODE_ENV === 'production') {
        throw new Error('Production environment requires JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_FILE');
      }
      this.activeKeyPair = generateEd25519KeyPair();
    }
  }

  getActiveKey(): KeyPairInfo {
    if (!this.activeKeyPair) {
      this.activeKeyPair = generateEd25519KeyPair();
    }
    return this.activeKeyPair;
  }

  setActiveKey(keyPair: KeyPairInfo) {
    if (this.activeKeyPair) {
      this.previousKeys.set(this.activeKeyPair.kid, this.activeKeyPair.publicKey);
      this.previousJwks.set(this.activeKeyPair.kid, this.activeKeyPair.jwk);
    }
    this.activeKeyPair = keyPair;
  }

  getPublicKey(kid: string): crypto.KeyObject | null {
    if (this.activeKeyPair && this.activeKeyPair.kid === kid) {
      return this.activeKeyPair.publicKey;
    }
    return this.previousKeys.get(kid) || null;
  }

  getJwks(): JwksResponse {
    const keys: Ed25519Jwk[] = [];
    if (this.activeKeyPair) {
      keys.push(this.activeKeyPair.jwk);
    }
    for (const jwk of this.previousJwks.values()) {
      keys.push(jwk);
    }
    return { keys };
  }
}

export const keyManager = new KeyManager();
