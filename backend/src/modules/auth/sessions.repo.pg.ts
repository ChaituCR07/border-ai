import pg from 'pg';
import { ISessionsRepo } from './sessions.repo.js';
import { Session, RevokeReason } from './sessions.types.js';

export class PgSessionsRepo implements ISessionsRepo {
  constructor(private pool: pg.Pool) {}

  private mapRow(row: any): Session {
    return {
      sessionId: row.session_id,
      userId: row.user_id,
      familyId: row.family_id,
      refreshHash: row.refresh_hash,
      issuedAt: new Date(row.issued_at),
      lastUsedAt: new Date(row.last_used_at),
      expiresAt: new Date(row.expires_at),
      absoluteExpiresAt: new Date(row.absolute_expires_at),
      rotatedAt: row.rotated_at ? new Date(row.rotated_at) : null,
      replacedBy: row.replaced_by,
      revokedAt: row.revoked_at ? new Date(row.revoked_at) : null,
      revokeReason: row.revoke_reason as RevokeReason | null,
      ip: row.ip,
      userAgentHash: row.user_agent_hash,
    };
  }

  async create(session: Session): Promise<Session> {
    const q = `
      INSERT INTO sessions (
        session_id, user_id, family_id, refresh_hash,
        issued_at, last_used_at, expires_at, absolute_expires_at,
        rotated_at, replaced_by, revoked_at, revoke_reason, ip, user_agent_hash
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
      RETURNING *;
    `;
    const res = await this.pool.query(q, [
      session.sessionId,
      session.userId,
      session.familyId,
      session.refreshHash,
      session.issuedAt,
      session.lastUsedAt,
      session.expiresAt,
      session.absoluteExpiresAt,
      session.rotatedAt ?? null,
      session.replacedBy ?? null,
      session.revokedAt ?? null,
      session.revokeReason ?? null,
      session.ip ?? null,
      session.userAgentHash ?? null,
    ]);
    return this.mapRow(res.rows[0]);
  }

  async findByRefreshHash(hash: string): Promise<Session | null> {
    const res = await this.pool.query('SELECT * FROM sessions WHERE refresh_hash = $1;', [hash]);
    if (res.rows.length === 0) return null;
    return this.mapRow(res.rows[0]);
  }

  async findById(sessionId: string): Promise<Session | null> {
    const res = await this.pool.query('SELECT * FROM sessions WHERE session_id = $1;', [sessionId]);
    if (res.rows.length === 0) return null;
    return this.mapRow(res.rows[0]);
  }

  async findByUserId(userId: string): Promise<Session[]> {
    const res = await this.pool.query(
      'SELECT * FROM sessions WHERE user_id = $1 ORDER BY issued_at DESC;',
      [userId]
    );
    return res.rows.map((r) => this.mapRow(r));
  }

  async update(session: Session): Promise<Session> {
    const q = `
      UPDATE sessions SET
        last_used_at = $2,
        expires_at = $3,
        rotated_at = $4,
        replaced_by = $5,
        revoked_at = $6,
        revoke_reason = $7
      WHERE session_id = $1
      RETURNING *;
    `;
    const res = await this.pool.query(q, [
      session.sessionId,
      session.lastUsedAt,
      session.expiresAt,
      session.rotatedAt ?? null,
      session.replacedBy ?? null,
      session.revokedAt ?? null,
      session.revokeReason ?? null,
    ]);
    return this.mapRow(res.rows[0]);
  }

  async revoke(sessionId: string, reason: string): Promise<void> {
    await this.pool.query(
      'UPDATE sessions SET revoked_at = now(), revoke_reason = $2 WHERE session_id = $1 AND revoked_at IS NULL;',
      [sessionId, reason]
    );
  }

  async revokeFamily(familyId: string, reason: string): Promise<void> {
    await this.pool.query(
      'UPDATE sessions SET revoked_at = now(), revoke_reason = $2 WHERE family_id = $1 AND revoked_at IS NULL;',
      [familyId, reason]
    );
  }

  async revokeAllForUser(userId: string, reason: string): Promise<void> {
    await this.pool.query(
      'UPDATE sessions SET revoked_at = now(), revoke_reason = $2 WHERE user_id = $1 AND revoked_at IS NULL;',
      [userId, reason]
    );
  }
}
