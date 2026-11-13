import { Session } from './sessions.types.js';

export interface ISessionsRepo {
  create(session: Session): Promise<Session>;
  findByRefreshHash(hash: string): Promise<Session | null>;
  findById(sessionId: string): Promise<Session | null>;
  findByUserId(userId: string): Promise<Session[]>;
  update(session: Session): Promise<Session>;
  revoke(sessionId: string, reason: string): Promise<void>;
  revokeFamily(familyId: string, reason: string): Promise<void>;
  revokeAllForUser(userId: string, reason: string): Promise<void>;
}
