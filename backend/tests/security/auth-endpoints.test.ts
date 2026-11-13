import { describe, it, expect, beforeEach, beforeAll } from 'vitest';
import { MemoryUsersRepo } from '../../src/modules/users/users.repo.memory.js';
import { MemorySessionsRepo } from '../../src/modules/auth/sessions.repo.memory.js';
import { SessionService } from '../../src/modules/auth/sessions.js';
import { AuthService } from '../../src/modules/auth/service.js';
import { hashPassword, setArgon2Params, initDummy } from '../../src/security/passwords.js';
import { verifyAccessToken } from '../../src/security/jwt.js';

describe('Auth Service & Login Endpoints', () => {
  let usersRepo: MemoryUsersRepo;
  let sessionsRepo: MemorySessionsRepo;
  let sessionService: SessionService;
  let authService: AuthService;

  beforeAll(async () => {
    setArgon2Params({ memory: 4096, passes: 1, parallelism: 1, tagLength: 32 });
    await initDummy();
  });

  beforeEach(async () => {
    usersRepo = new MemoryUsersRepo();
    sessionsRepo = new MemorySessionsRepo();
    sessionService = new SessionService(sessionsRepo);
    authService = new AuthService(usersRepo, sessionService);

    // Create a test user
    const passwordHash = await hashPassword('AdminPassword2026!');
    await usersRepo.create({
      username: 'admin',
      email: 'admin@border.gov',
      displayName: 'System Admin',
      role: 'ADMIN',
      passwordHash,
    });
  });

  it('authenticates valid credentials and issues valid EdDSA access token and refresh token', async () => {
    const result = await authService.login('admin', 'AdminPassword2026!');
    expect(result.accessToken).toBeDefined();
    expect(result.refreshToken).toBeDefined();
    expect(result.user.username).toBe('admin');
    expect(result.user.role).toBe('ADMIN');

    // Verify token cryptographically
    const claims = verifyAccessToken(result.accessToken);
    expect(claims.sub).toBe(result.user.userId);
    expect(claims.role).toBe('ADMIN');
  });

  it('returns generic error on wrong password (anti-enumeration)', async () => {
    await expect(authService.login('admin', 'WrongPass1234!')).rejects.toThrowError(
      /Invalid username or password/i
    );
  });

  it('returns generic error on non-existent user (anti-enumeration)', async () => {
    await expect(authService.login('ghost_user', 'WrongPass1234!')).rejects.toThrowError(
      /Invalid username or password/i
    );
  });

  it('rotates refresh token and issues new access token', async () => {
    const loginRes = await authService.login('admin', 'AdminPassword2026!');
    const refreshRes = await authService.refresh(loginRes.refreshToken);

    expect(refreshRes.accessToken).toBeDefined();
    expect(refreshRes.refreshToken).toBeDefined();
    expect(refreshRes.refreshToken).not.toBe(loginRes.refreshToken);

    const claims = verifyAccessToken(refreshRes.accessToken);
    expect(claims.sub).toBe(loginRes.user.userId);
  });

  it('allows user to change password and invalidates prior sessions', async () => {
    const loginRes = await authService.login('admin', 'AdminPassword2026!');

    await authService.changePassword(
      loginRes.user.userId,
      'AdminPassword2026!',
      'NewStrongerPassword2026!'
    );

    // Prior refresh token is now revoked
    await expect(authService.refresh(loginRes.refreshToken)).rejects.toThrowError(
      /Session expired or refresh token invalid/i
    );

    // Login with new password succeeds
    const newLogin = await authService.login('admin', 'NewStrongerPassword2026!');
    expect(newLogin.accessToken).toBeDefined();
  });
});
