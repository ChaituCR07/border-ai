import crypto from 'node:crypto';
import { keyManager } from './keys.js';

export type Role = 'ADMIN' | 'OPERATOR' | 'INVESTIGATOR' | 'VIEWER';

export class AuthError extends Error {
  constructor(
    public readonly code: string,
    message: string
  ) {
    super(message);
    this.name = 'AuthError';
  }
}

export interface AccessClaims {
  iss: 'border-ai';
  aud: 'border-ai-api';
  sub: string;           // user_id
  role: Role;
  sid: string;           // session_id
  ver: number;           // token_version
  iat: number;
  exp: number;
  jti: string;
}

export interface StreamClaims {
  iss: 'border-ai';
  aud: 'border-ai-stream';
  sub: string;           // user_id
  cam: string;           // camera_id
  iat: number;
  exp: number;
}

export const ACCESS_TOKEN_TTL_SECONDS = 600; // 10 minutes
export const STREAM_TOKEN_TTL_SECONDS = 60;  // 60 seconds connection window

function base64urlEncode(buf: Buffer): string {
  return buf.toString('base64url');
}

function base64urlDecode(str: string): Buffer {
  return Buffer.from(str, 'base64url');
}

/**
 * Sign an EdDSA (Ed25519) Access Token
 */
export function signAccessToken(params: {
  userId: string;
  role: Role;
  sessionId: string;
  tokenVersion: number;
  ttlSeconds?: number;
}): string {
  const activeKey = keyManager.getActiveKey();
  const now = Math.floor(Date.now() / 1000);
  const ttl = params.ttlSeconds ?? ACCESS_TOKEN_TTL_SECONDS;

  const header = {
    alg: 'EdDSA',
    kid: activeKey.kid,
    typ: 'JWT',
  };

  const payload: AccessClaims = {
    iss: 'border-ai',
    aud: 'border-ai-api',
    sub: params.userId,
    role: params.role,
    sid: params.sessionId,
    ver: params.tokenVersion,
    iat: now,
    exp: now + ttl,
    jti: crypto.randomUUID(),
  };

  const headerB64 = base64urlEncode(Buffer.from(JSON.stringify(header)));
  const payloadB64 = base64urlEncode(Buffer.from(JSON.stringify(payload)));
  const signingInput = Buffer.from(`${headerB64}.${payloadB64}`);

  const signature = crypto.sign(null, signingInput, activeKey.privateKey);
  const signatureB64 = base64urlEncode(signature);

  return `${headerB64}.${payloadB64}.${signatureB64}`;
}

/**
 * Sign an EdDSA (Ed25519) Stream Token for MJPEG live viewing
 */
export function signStreamToken(params: {
  userId: string;
  cameraId: string;
  ttlSeconds?: number;
}): string {
  const activeKey = keyManager.getActiveKey();
  const now = Math.floor(Date.now() / 1000);
  const ttl = params.ttlSeconds ?? STREAM_TOKEN_TTL_SECONDS;

  const header = {
    alg: 'EdDSA',
    kid: activeKey.kid,
    typ: 'stream+jwt',
  };

  const payload: StreamClaims = {
    iss: 'border-ai',
    aud: 'border-ai-stream',
    sub: params.userId,
    cam: params.cameraId,
    iat: now,
    exp: now + ttl,
  };

  const headerB64 = base64urlEncode(Buffer.from(JSON.stringify(header)));
  const payloadB64 = base64urlEncode(Buffer.from(JSON.stringify(payload)));
  const signingInput = Buffer.from(`${headerB64}.${payloadB64}`);

  const signature = crypto.sign(null, signingInput, activeKey.privateKey);
  const signatureB64 = base64urlEncode(signature);

  return `${headerB64}.${payloadB64}.${signatureB64}`;
}

/**
 * Verify and decode an EdDSA Access Token
 */
export function verifyAccessToken(
  token: string,
  options: { clockTolerance?: number } = {}
): AccessClaims {
  if (token.length > 4096) {
    throw new AuthError('TOKEN_TOO_LARGE', 'Token length exceeds maximum allowed limit of 4096 bytes');
  }

  const parts = token.split('.');
  if (parts.length !== 3) {
    throw new AuthError('INVALID_TOKEN_FORMAT', 'Token must contain exactly 3 segments separated by dots');
  }

  const [headerB64, payloadB64, signatureB64] = parts;
  if (!headerB64 || !payloadB64 || !signatureB64) {
    throw new AuthError('INVALID_TOKEN_FORMAT', 'Token must contain non-empty segments');
  }

  let header: any;
  try {
    header = JSON.parse(base64urlDecode(headerB64).toString('utf-8'));
  } catch {
    throw new AuthError('MALFORMED_HEADER', 'Malformed token header JSON');
  }

  // Strict algorithm check: MUST be EdDSA
  if (header.alg !== 'EdDSA') {
    throw new AuthError('UNSUPPORTED_ALGORITHM', `Algorithm '${header.alg}' is not permitted; EdDSA required`);
  }

  if (header.typ !== 'JWT') {
    throw new AuthError('INVALID_TOKEN_TYPE', `Header typ must be 'JWT', received '${header.typ}'`);
  }

  if (!header.kid) {
    throw new AuthError('MISSING_KEY_ID', 'Token header missing kid');
  }

  const publicKey = keyManager.getPublicKey(header.kid);
  if (!publicKey) {
    throw new AuthError('UNKNOWN_KEY', `Key with kid '${header.kid}' is not recognized`);
  }

  const signingInput = Buffer.from(`${headerB64}.${payloadB64}`);
  const signature = base64urlDecode(signatureB64);

  const isValidSig = crypto.verify(null, signingInput, publicKey, signature);
  if (!isValidSig) {
    throw new AuthError('INVALID_SIGNATURE', 'Cryptographic signature verification failed');
  }

  let payload: any;
  try {
    payload = JSON.parse(base64urlDecode(payloadB64).toString('utf-8'));
  } catch {
    throw new AuthError('MALFORMED_PAYLOAD', 'Malformed token payload JSON');
  }

  // Claims enforcement
  if (payload.iss !== 'border-ai') {
    throw new AuthError('INVALID_ISSUER', `Issuer must be 'border-ai', received '${payload.iss}'`);
  }

  if (payload.aud !== 'border-ai-api') {
    throw new AuthError('INVALID_AUDIENCE', `Audience must be 'border-ai-api', received '${payload.aud}'`);
  }

  const tolerance = options.clockTolerance ?? 5;
  const now = Math.floor(Date.now() / 1000);

  if (typeof payload.exp !== 'number' || payload.exp < now - tolerance) {
    throw new AuthError('TOKEN_EXPIRED', 'Token has expired');
  }

  for (const claim of ['sub', 'role', 'sid', 'ver', 'jti'] as const) {
    if (payload[claim] === undefined || payload[claim] === null) {
      throw new AuthError('MISSING_CLAIM', `Missing mandatory claim '${claim}' in access token`);
    }
  }

  const validRoles: Role[] = ['ADMIN', 'OPERATOR', 'INVESTIGATOR', 'VIEWER'];
  if (!validRoles.includes(payload.role)) {
    throw new AuthError('INVALID_ROLE', `Role '${payload.role}' is not recognized`);
  }

  return payload as AccessClaims;
}
