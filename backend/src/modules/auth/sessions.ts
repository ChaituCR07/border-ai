import crypto from 'node:crypto';
import { ISessionsRepo } from './sessions.repo.js';
import {
  Session,
  CreateSessionParams,
  RotateResult,
} from './sessions.types.js';

export const IDLE_EXPIRY_MS = 8 * 60 * 60 * 1000;      // 8 hours sliding window
export const ABSOLUTE_EXPIRY_MS = 12 * 60 * 60 * 1000; // 12 hours absolute limit
export const REFRESH_GRACE_WINDOW_MS = 5000;           // 5 seconds multi-tab race grace window

export function hashRefreshToken(rawToken: string): string {
  return crypto.createHash('sha256').update(rawToken).digest('hex');
}

export function generateRefreshToken(): string {
  return crypto.randomBytes(32).toString('base64url');
}

export class SessionService {
  constructor(private repo: ISessionsRepo) {}

  /**
   * Create an initial login session and return the raw refresh token
   */
  async createSession(params: CreateSessionParams): Promise<{ session: Session; refreshToken: string }> {
    const rawRefreshToken = generateRefreshToken();
    const refreshHash = hashRefreshToken(rawRefreshToken);
    const now = new Date();
    const idleTtl = params.idleTtlMs ?? IDLE_EXPIRY_MS;
    const absoluteTtl = params.absoluteTtlMs ?? ABSOLUTE_EXPIRY_MS;

    const userAgentHash = params.userAgent
      ? crypto.createHash('sha256').update(params.userAgent).digest('hex').slice(0, 16)
      : null;

    const session: Session = {
      sessionId: crypto.randomUUID(),
      userId: params.userId,
      familyId: params.familyId ?? crypto.randomUUID(),
      refreshHash,
      issuedAt: now,
      lastUsedAt: now,
      expiresAt: new Date(now.getTime() + idleTtl),
      absoluteExpiresAt: new Date(now.getTime() + absoluteTtl),
      rotatedAt: null,
      replacedBy: null,
      revokedAt: null,
      revokeReason: null,
      ip: params.ip ?? null,
      userAgentHash,
    };

    const created = await this.repo.create(session);
    return { session: created, refreshToken: rawRefreshToken };
  }

  /**
   * Rotate a refresh token with 5-second multi-tab grace and reuse detection
   */
  async rotateRefreshToken(
    rawRefreshToken: string,
    meta?: { ip?: string; userAgent?: string }
  ): Promise<RotateResult> {
    const hash = hashRefreshToken(rawRefreshToken);
    const existing = await this.repo.findByRefreshHash(hash);

    if (!existing) {
      return { success: false, reason: 'UNKNOWN_TOKEN' };
    }

    const now = new Date();

    // 1. Check if explicitly revoked
    if (existing.revokedAt) {
      return { success: false, reason: 'REVOKED' };
    }

    // 2. Check if already rotated
    if (existing.rotatedAt) {
      const elapsedSinceRotation = now.getTime() - existing.rotatedAt.getTime();
      if (elapsedSinceRotation <= REFRESH_GRACE_WINDOW_MS) {
        // Multi-tab race condition grace window: return active session without rotating cookie again
        return { success: true, session: existing, grace: true };
      }

      // Reuse detected outside grace window -> revoke entire token family!
      await this.repo.revokeFamily(existing.familyId, 'REUSE');
      return { success: false, reason: 'REUSE_DETECTED' };
    }

    // 3. Check expiration
    if (now > existing.expiresAt || now > existing.absoluteExpiresAt) {
      return { success: false, reason: 'EXPIRED' };
    }

    // 4. Normal rotation: issue successor
    const newRawRefreshToken = generateRefreshToken();
    const newRefreshHash = hashRefreshToken(newRawRefreshToken);

    const userAgentHash = meta?.userAgent
      ? crypto.createHash('sha256').update(meta.userAgent).digest('hex').slice(0, 16)
      : existing.userAgentHash;

    const successorId = crypto.randomUUID();
    const successor: Session = {
      sessionId: successorId,
      userId: existing.userId,
      familyId: existing.familyId,
      refreshHash: newRefreshHash,
      issuedAt: now,
      lastUsedAt: now,
      expiresAt: new Date(now.getTime() + IDLE_EXPIRY_MS),
      absoluteExpiresAt: existing.absoluteExpiresAt, // preserves absolute limit across rotations
      rotatedAt: null,
      replacedBy: null,
      revokedAt: null,
      revokeReason: null,
      ip: meta?.ip ?? existing.ip,
      userAgentHash,
    };

    // Mark current rotated
    existing.rotatedAt = now;
    existing.lastUsedAt = now;
    existing.replacedBy = successorId;

    await this.repo.update(existing);
    const createdSuccessor = await this.repo.create(successor);

    return {
      success: true,
      session: createdSuccessor,
      refreshToken: newRawRefreshToken,
      grace: false,
    };
  }

  async revokeSession(sessionId: string, reason = 'LOGOUT'): Promise<void> {
    await this.repo.revoke(sessionId, reason);
  }

  async revokeAllUserSessions(userId: string, reason = 'LOGOUT_ALL'): Promise<void> {
    await this.repo.revokeAllForUser(userId, reason);
  }

  async revokeFamily(familyId: string, reason = 'REUSE'): Promise<void> {
    await this.repo.revokeFamily(familyId, reason);
  }

  async getUserSessions(userId: string): Promise<Session[]> {
    return this.repo.findByUserId(userId);
  }

  async getSession(sessionId: string): Promise<Session | null> {
    return this.repo.findById(sessionId);
  }
}
