import { describe, it, expect, beforeAll } from 'vitest';
import { MemoryUsersRepo } from '../../src/modules/users/users.repo.memory.js';
import { hashPassword, validatePassword, setArgon2Params, initDummy } from '../../src/security/passwords.js';

describe('Admin Bootstrap & Policy Verification', () => {
  let repo: MemoryUsersRepo;

  beforeAll(async () => {
    setArgon2Params({ memory: 4096, passes: 1, parallelism: 1, tagLength: 32 });
    await initDummy();
  });

  beforeEach(() => {
    repo = new MemoryUsersRepo();
  });

  it('detects zero active admins prior to bootstrap', async () => {
    const adminCount = await repo.countActiveAdmins();
    expect(adminCount).toBe(0);
  });

  it('successfully creates the first admin with compliant password', async () => {
    const username = 'admin';
    const password = 'SuperSecureRootPassword2026!';

    const policy = await validatePassword(password, { username });
    expect(policy.valid).toBe(true);

    const hash = await hashPassword(password);
    const created = await repo.create({
      username,
      role: 'ADMIN',
      passwordHash: hash,
    });

    expect(created.userId).toBeDefined();
    expect(created.role).toBe('ADMIN');
    expect(created.status).toBe('ACTIVE');

    const adminCount = await repo.countActiveAdmins();
    expect(adminCount).toBe(1);
  });

  it('rejects bootstrap with weak password', async () => {
    const policy = await validatePassword('weak123', { username: 'admin' });
    expect(policy.valid).toBe(false);
    expect(policy.errors).toContain('PASSWORD_TOO_SHORT');
  });
});
