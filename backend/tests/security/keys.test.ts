import { describe, it, expect } from 'vitest';
import crypto from 'node:crypto';
import { generateEd25519KeyPair, deriveKeyId, keyManager } from '../../src/security/keys.js';

describe('Ed25519 Key Management & JWKS', () => {
  it('generates an Ed25519 key pair with valid kid and JWK format', () => {
    const pair = generateEd25519KeyPair();
    expect(pair.kid).toBeDefined();
    expect(pair.kid.length).toBe(16);
    expect(pair.jwk.kty).toBe('OKP');
    expect(pair.jwk.crv).toBe('Ed25519');
    expect(pair.jwk.alg).toBe('EdDSA');
    expect(pair.jwk.use).toBe('sig');
    expect(pair.jwk.x).toBeDefined();

    // Verify signing and verification
    const payload = Buffer.from('test-payload');
    const signature = crypto.sign(null, payload, pair.privateKey);
    const valid = crypto.verify(null, payload, pair.publicKey, signature);
    expect(valid).toBe(true);
  });

  it('correctly derives deterministic kid from public key SPKI DER', () => {
    const pair = generateEd25519KeyPair();
    const derived = deriveKeyId(pair.publicKey);
    expect(derived).toBe(pair.kid);
  });

  it('serves JWKS containing the active public key', () => {
    const jwks = keyManager.getJwks();
    expect(jwks.keys.length).toBeGreaterThanOrEqual(1);
    const active = keyManager.getActiveKey();
    const found = jwks.keys.find((k) => k.kid === active.kid);
    expect(found).toBeDefined();
    expect(found?.kty).toBe('OKP');
    expect(found?.crv).toBe('Ed25519');
  });

  it('supports key rotation and retrieves previous keys by kid', () => {
    const original = keyManager.getActiveKey();
    const fresh = generateEd25519KeyPair();

    keyManager.setActiveKey(fresh);
    expect(keyManager.getActiveKey().kid).toBe(fresh.kid);

    // Old key is still retrievable for verification
    const retrievedOld = keyManager.getPublicKey(original.kid);
    expect(retrievedOld).not.toBeNull();

    // Reset back
    keyManager.setActiveKey(original);
  });
});
