import { ISessionsRepo } from './sessions.repo.js';
import { Session, RevokeReason } from './sessions.types.js';

export class MemorySessionsRepo implements ISessionsRepo {
  private sessions = new Map<string, Session>(); // sessionId -> Session
  private hashIndex = new Map<string, string>();  // refreshHash -> sessionId

  async create(session: Session): Promise<Session> {
    const copy = { ...session };
    this.sessions.set(session.sessionId, copy);
    this.hashIndex.set(session.refreshHash, session.sessionId);
    return copy;
  }

  async findByRefreshHash(hash: string): Promise<Session | null> {
    const id = this.hashIndex.get(hash);
    if (!id) return null;
    const s = this.sessions.get(id);
    return s ? { ...s } : null;
  }

  async findById(sessionId: string): Promise<Session | null> {
    const s = this.sessions.get(sessionId);
    return s ? { ...s } : null;
  }

  async findByUserId(userId: string): Promise<Session[]> {
    const results: Session[] = [];
    for (const s of this.sessions.values()) {
      if (s.userId === userId) {
        results.push({ ...s });
      }
    }
    return results.sort((a, b) => b.issuedAt.getTime() - a.issuedAt.getTime());
  }

  async update(session: Session): Promise<Session> {
    const copy = { ...session };
    this.sessions.set(session.sessionId, copy);
    this.hashIndex.set(session.refreshHash, session.sessionId);
    return copy;
  }

  async revoke(sessionId: string, reason: string): Promise<void> {
    const s = this.sessions.get(sessionId);
    if (s && !s.revokedAt) {
      s.revokedAt = new Date();
      s.revokeReason = reason as RevokeReason;
    }
  }

  async revokeFamily(familyId: string, reason: string): Promise<void> {
    const now = new Date();
    for (const s of this.sessions.values()) {
      if (s.familyId === familyId && !s.revokedAt) {
        s.revokedAt = now;
        s.revokeReason = reason as RevokeReason;
      }
    }
  }

  async revokeAllForUser(userId: string, reason: string): Promise<void> {
    const now = new Date();
    for (const s of this.sessions.values()) {
      if (s.userId === userId && !s.revokedAt) {
        s.revokedAt = now;
        s.revokeReason = reason as RevokeReason;
      }
    }
  }

  clear() {
    this.sessions.clear();
    this.hashIndex.clear();
  }
}
