import { describe, it, expect, beforeEach, beforeAll } from 'vitest';
import { MemoryUsersRepo } from '../../src/modules/users/users.repo.memory.js';
import { UsersService } from '../../src/modules/users/service.js';
import { setArgon2Params, initDummy } from '../../src/security/passwords.js';

describe('User Management & Last-Admin Safety Rails', () => {
  let repo: MemoryUsersRepo;
  let service: UsersService;

  beforeAll(async () => {
    setArgon2Params({ memory: 4096, passes: 1, parallelism: 1, tagLength: 32 });
    await initDummy();
  });

  beforeEach(async () => {
    repo = new MemoryUsersRepo();
    service = new UsersService(repo);

    // Seed first admin
    await service.createUser({
      username: 'root_admin',
      role: 'ADMIN',
      password: 'InitialPassword123!',
    });
  });

  it('lists users without leaking password hashes', async () => {
    const users = await service.listUsers();
    expect(users.length).toBe(1);
    expect(users[0]?.username).toBe('root_admin');
    expect((users[0] as any).passwordHash).toBeUndefined();
    expect((users[0] as any).passwordHistory).toBeUndefined();
  });

  it('creates new operator user successfully', async () => {
    const created = await service.createUser({
      username: 'operator_dan',
      role: 'OPERATOR',
      password: 'OperatorPassword123!',
    });

    expect(created.userId).toBeDefined();
    expect(created.username).toBe('operator_dan');
    expect(created.role).toBe('OPERATOR');
  });

  it('prevents demoting the last active administrator (409 conflict)', async () => {
    const admin = (await repo.list())[0]!;

    await expect(
      service.updateUser(admin.userId, { role: 'OPERATOR' })
    ).rejects.toThrowError(/Cannot disable or demote the last remaining active administrator/i);
  });

  it('prevents disabling the last active administrator (409 conflict)', async () => {
    const admin = (await repo.list())[0]!;

    await expect(
      service.disableUser(admin.userId)
    ).rejects.toThrowError(/Cannot disable the last remaining active administrator/i);
  });

  it('allows demoting an admin when multiple active admins exist', async () => {
    const secondAdmin = await service.createUser({
      username: 'second_admin',
      role: 'ADMIN',
      password: 'SecondAdminPassword123!',
    });

    // Demote second admin is allowed because root_admin is still active
    const demoted = await service.updateUser(secondAdmin.userId, { role: 'INVESTIGATOR' });
    expect(demoted.role).toBe('INVESTIGATOR');
  });

  it('resets user password, sets must_change_password=true, and bumps token_version', async () => {
    const operator = await service.createUser({
      username: 'op_reset_test',
      role: 'OPERATOR',
      password: 'OldPassword12345!',
    });

    const resetRes = await service.resetPassword(operator.userId);
    expect(resetRes.temporaryPassword).toBeDefined();
    expect(resetRes.mustChangePassword).toBe(true);

    const updated = await repo.findById(operator.userId);
    expect(updated?.mustChangePassword).toBe(true);
    expect(updated?.tokenVersion).toBe(operator.tokenVersion + 1);
  });
});
