import { describe, it, expect } from 'vitest';
import crypto from 'node:crypto';
import {
  signAccessToken,
  verifyAccessToken,
  signStreamToken,
  AuthError,
  ACCESS_TOKEN_TTL_SECONDS,
} from '../../src/security/jwt.js';
import { keyManager, generateEd25519KeyPair } from '../../src/security/keys.js';

describe('EdDSA JWT Signing & Attack Defenses', () => {
  const userId = 'usr-1111-2222';
  const sessionId = 'ses-3333-4444';
  const role = 'INVESTIGATOR';
  const tokenVersion = 1;

  it('signs and verifies a valid access token', () => {
    const token = signAccessToken({ userId, role, sessionId, tokenVersion });
    const claims = verifyAccessToken(token);

    expect(claims.sub).toBe(userId);
    expect(claims.role).toBe(role);
    expect(claims.sid).toBe(sessionId);
    expect(claims.ver).toBe(tokenVersion);
    expect(claims.iss).toBe('border-ai');
    expect(claims.aud).toBe('border-ai-api');
    expect(claims.jti).toBeDefined();
    expect(claims.exp - claims.iat).toBe(ACCESS_TOKEN_TTL_SECONDS);
  });

  it('rejects "alg: none" attack', () => {
    const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT', kid: keyManager.getActiveKey().kid })).toString('base64url');
    const payload = Buffer.from(
      JSON.stringify({
        iss: 'border-ai',
        aud: 'border-ai-api',
        sub: userId,
        role: 'ADMIN',
        sid: sessionId,
        ver: tokenVersion,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 600,
        jti: 'jti-attack-1',
      })
    ).toString('base64url');

    const noneTokenWithSig = `${header}.${payload}.none_sig`;
    expect(() => verifyAccessToken(noneTokenWithSig)).toThrowError(AuthError);
    expect(() => verifyAccessToken(noneTokenWithSig)).toThrowError(/not permitted/);

    const noneTokenEmptySig = `${header}.${payload}.`;
    expect(() => verifyAccessToken(noneTokenEmptySig)).toThrowError(AuthError);
  });

  it('rejects algorithm confusion (HMAC using public key as secret)', () => {
    const activeKey = keyManager.getActiveKey();
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: activeKey.kid })).toString('base64url');
    const payload = Buffer.from(
      JSON.stringify({
        iss: 'border-ai',
        aud: 'border-ai-api',
        sub: userId,
        role: 'ADMIN',
        sid: sessionId,
        ver: tokenVersion,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 600,
        jti: 'jti-attack-2',
      })
    ).toString('base64url');

    const hmacSig = crypto.createHmac('sha256', activeKey.publicKeyPem).update(`${header}.${payload}`).digest('base64url');
    const attackToken = `${header}.${payload}.${hmacSig}`;

    expect(() => verifyAccessToken(attackToken)).toThrowError(AuthError);
    expect(() => verifyAccessToken(attackToken)).toThrowError(/not permitted/);
  });

  it('rejects expired tokens', () => {
    const expiredToken = signAccessToken({
      userId,
      role,
      sessionId,
      tokenVersion,
      ttlSeconds: -10, // 10 seconds in the past
    });

    expect(() => verifyAccessToken(expiredToken)).toThrowError(AuthError);
    expect(() => verifyAccessToken(expiredToken)).toThrowError(/expired/i);
  });

  it('rejects tampered payload', () => {
    const validToken = signAccessToken({ userId, role: 'VIEWER', sessionId, tokenVersion });
    const [h, p, s] = validToken.split('.');

    // Tamper payload from VIEWER to ADMIN
    const decoded = JSON.parse(Buffer.from(p, 'base64url').toString('utf-8'));
    decoded.role = 'ADMIN';
    const tamperedPayload = Buffer.from(JSON.stringify(decoded)).toString('base64url');

    const tamperedToken = `${h}.${tamperedPayload}.${s}`;
    expect(() => verifyAccessToken(tamperedToken)).toThrowError(AuthError);
    expect(() => verifyAccessToken(tamperedToken)).toThrowError(/signature verification failed/i);
  });

  it('rejects unknown key IDs', () => {
    const rogueKey = generateEd25519KeyPair();
    const now = Math.floor(Date.now() / 1000);
    const header = Buffer.from(JSON.stringify({ alg: 'EdDSA', typ: 'JWT', kid: 'unknown-key-9999' })).toString('base64url');
    const payload = Buffer.from(
      JSON.stringify({
        iss: 'border-ai',
        aud: 'border-ai-api',
        sub: userId,
        role: 'ADMIN',
        sid: sessionId,
        ver: tokenVersion,
        iat: now,
        exp: now + 600,
        jti: 'jti-attack-3',
      })
    ).toString('base64url');

    const sig = crypto.sign(null, Buffer.from(`${header}.${payload}`), rogueKey.privateKey).toString('base64url');
    const rogueToken = `${header}.${payload}.${sig}`;

    expect(() => verifyAccessToken(rogueToken)).toThrowError(AuthError);
    expect(() => verifyAccessToken(rogueToken)).toThrowError(/not recognized/i);
  });

  it('rejects tokens larger than 4096 bytes', () => {
    const giantPayload = 'A'.repeat(5000);
    expect(() => verifyAccessToken(giantPayload)).toThrowError(AuthError);
    expect(() => verifyAccessToken(giantPayload)).toThrowError(/exceeds maximum allowed limit/i);
  });

  it('signs stream token with typ=stream+jwt and aud=border-ai-stream', () => {
    const streamToken = signStreamToken({ userId, cameraId: 'cam-gate-01' });
    const [h, p] = streamToken.split('.');
    const header = JSON.parse(Buffer.from(h, 'base64url').toString('utf-8'));
    const payload = JSON.parse(Buffer.from(p, 'base64url').toString('utf-8'));

    expect(header.typ).toBe('stream+jwt');
    expect(header.alg).toBe('EdDSA');
    expect(payload.aud).toBe('border-ai-stream');
    expect(payload.cam).toBe('cam-gate-01');
    expect(payload.sub).toBe(userId);
  });
});
