import { describe, it, expect, beforeEach } from 'vitest';
import { MemorySessionsRepo } from '../../src/modules/auth/sessions.repo.memory.js';
import { SessionService, REFRESH_GRACE_WINDOW_MS } from '../../src/modules/auth/sessions.js';

describe('Rotating Refresh Tokens & Reuse Detection', () => {
  let repo: MemorySessionsRepo;
  let service: SessionService;
  const userId = 'usr-test-1234';

  beforeEach(() => {
    repo = new MemorySessionsRepo();
    service = new SessionService(repo);
  });

  it('creates an initial session with familyId and hashed token', async () => {
    const { session, refreshToken } = await service.createSession({ userId });
    expect(session.userId).toBe(userId);
    expect(session.familyId).toBeDefined();
    expect(session.refreshHash).toBeDefined();
    expect(refreshToken).toBeDefined();

    // The raw token is NOT stored directly
    expect(session.refreshHash).not.toBe(refreshToken);
  });

  it('rotates refresh token normally on first use', async () => {
    const { session: firstSession, refreshToken: token1 } = await service.createSession({ userId });

    const result = await service.rotateRefreshToken(token1);
    expect(result.success).toBe(true);
    if (!result.success) return;

    expect(result.grace).toBe(false);
    expect(result.refreshToken).toBeDefined();
    expect(result.refreshToken).not.toBe(token1);
    expect(result.session.familyId).toBe(firstSession.familyId);

    // Old session marked rotated
    const oldSession = await repo.findById(firstSession.sessionId);
    expect(oldSession?.rotatedAt).not.toBeNull();
    expect(oldSession?.replacedBy).toBe(result.session.sessionId);
  });

  it('permits reuse within the 5-second grace window (multi-tab race)', async () => {
    const { refreshToken: token1 } = await service.createSession({ userId });

    // First rotation (Tab 1)
    const rot1 = await service.rotateRefreshToken(token1);
    expect(rot1.success).toBe(true);

    // Immediate second rotation with same token (Tab 2) within grace window
    const rot2 = await service.rotateRefreshToken(token1);
    expect(rot2.success).toBe(true);
    if (!rot2.success) return;

    expect(rot2.grace).toBe(true);
    expect(rot2.refreshToken).toBeUndefined(); // no new cookie issued
  });

  it('revokes entire token family when reuse is detected outside grace window', async () => {
    const { session: firstSession, refreshToken: token1 } = await service.createSession({ userId });

    // Rotate token1 -> token2
    const rot1 = await service.rotateRefreshToken(token1);
    expect(rot1.success).toBe(true);

    // Manually push rotatedAt back by 10 seconds to simulate elapsed grace window
    const old = await repo.findById(firstSession.sessionId);
    if (old) {
      old.rotatedAt = new Date(Date.now() - (REFRESH_GRACE_WINDOW_MS + 5000));
      await repo.update(old);
    }

    // Attacker tries to reuse token1 after grace window has expired
    const attackResult = await service.rotateRefreshToken(token1);
    expect(attackResult.success).toBe(false);
    if (attackResult.success) return;

    expect(attackResult.reason).toBe('REUSE_DETECTED');

    // Both old session and successor in the family are now revoked!
    const updatedSuccessor = await repo.findById(rot1.session.sessionId);
    expect(updatedSuccessor?.revokedAt).not.toBeNull();
    expect(updatedSuccessor?.revokeReason).toBe('REUSE');
  });

  it('revokes user sessions on logout and logout-all', async () => {
    const { session: s1 } = await service.createSession({ userId });
    const { session: s2 } = await service.createSession({ userId });

    await service.revokeSession(s1.sessionId, 'LOGOUT');
    const checkedS1 = await repo.findById(s1.sessionId);
    expect(checkedS1?.revokedAt).not.toBeNull();
    expect(checkedS1?.revokeReason).toBe('LOGOUT');

    // S2 is still active
    const checkedS2Before = await repo.findById(s2.sessionId);
    expect(checkedS2Before?.revokedAt).toBeNull();

    // Logout all
    await service.revokeAllUserSessions(userId, 'LOGOUT_ALL');
    const checkedS2After = await repo.findById(s2.sessionId);
    expect(checkedS2After?.revokedAt).not.toBeNull();
    expect(checkedS2After?.revokeReason).toBe('LOGOUT_ALL');
  });
});
