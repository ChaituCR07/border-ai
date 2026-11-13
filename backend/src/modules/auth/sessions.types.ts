export type RevokeReason =
  | 'LOGOUT'
  | 'LOGOUT_ALL'
  | 'REUSE'
  | 'PASSWORD_CHANGE'
  | 'ADMIN'
  | 'DISABLED';

export interface Session {
  sessionId: string;
  userId: string;
  familyId: string;
  refreshHash: string;
  issuedAt: Date;
  lastUsedAt: Date;
  expiresAt: Date;
  absoluteExpiresAt: Date;
  rotatedAt?: Date | null;
  replacedBy?: string | null;
  revokedAt?: Date | null;
  revokeReason?: RevokeReason | null;
  ip?: string | null;
  userAgentHash?: string | null;
}

export interface CreateSessionParams {
  userId: string;
  familyId?: string;
  ip?: string;
  userAgent?: string;
  idleTtlMs?: number;      // default 8 hours
  absoluteTtlMs?: number;  // default 12 hours
}

export type RotateResult =
  | { success: true; session: Session; refreshToken: string; grace?: false }
  | { success: true; session: Session; refreshToken?: undefined; grace: true }
  | { success: false; reason: 'UNKNOWN_TOKEN' | 'REVOKED' | 'EXPIRED' | 'REUSE_DETECTED' };
