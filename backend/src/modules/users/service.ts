import crypto from 'node:crypto';
import { IUsersRepo } from './users.repo.js';
import { CreateUserInput, UpdateUserInput } from './schemas.js';
import { hashPassword, validatePassword } from '../../security/passwords.js';
import { AppError } from '../../common/errors.js';
import { User } from './users.types.js';

export interface UserAuditSink {
  log(entry: {
    actor: string;
    action: string;
    entityType: string;
    entityId: string;
    detail?: Record<string, any>;
  }): Promise<void>;
}

export class UsersService {
  constructor(
    private repo: IUsersRepo,
    private auditSink?: UserAuditSink
  ) {}

  private async audit(action: string, entityId: string, actor: string, detail?: Record<string, any>) {
    if (this.auditSink) {
      try {
        await this.auditSink.log({
          actor,
          action,
          entityType: 'USER',
          entityId,
          detail,
        });
      } catch (err: any) {
        console.warn(`[users] Audit log failed: ${err.message}`);
      }
    }
  }

  async listUsers(): Promise<Omit<User, 'passwordHash' | 'passwordHistory'>[]> {
    const all = await this.repo.list();
    return all.map(({ passwordHash, passwordHistory, ...safe }) => safe);
  }

  async getUser(userId: string): Promise<Omit<User, 'passwordHash' | 'passwordHistory'> | null> {
    const user = await this.repo.findById(userId);
    if (!user) return null;
    const { passwordHash, passwordHistory, ...safe } = user;
    return safe;
  }

  async createUser(input: CreateUserInput, actor = 'admin'): Promise<Omit<User, 'passwordHash' | 'passwordHistory'>> {
    const existing = await this.repo.findByUsername(input.username);
    if (existing) {
      throw new AppError(409, 'CONFLICT', `Username '${input.username}' already exists`);
    }

    const isGenerated = !input.password;
    const rawPassword =
      input.password || `SecurePass!_${crypto.randomBytes(8).toString('base64url')}2026`;

    const policy = await validatePassword(rawPassword, {
      username: input.username,
      email: input.email,
    });

    if (!policy.valid) {
      throw new AppError(400, 'PASSWORD_POLICY_VIOLATION', policy.errors.join(', '));
    }

    const passwordHash = await hashPassword(rawPassword);

    const created = await this.repo.create({
      username: input.username,
      email: input.email,
      displayName: input.displayName,
      role: input.role,
      passwordHash,
      mustChangePassword: isGenerated,
      createdBy: actor,
    });

    await this.audit('USER_CREATE', created.userId, actor, {
      username: created.username,
      role: created.role,
    });

    const { passwordHash: _, passwordHistory: __, ...safe } = created;
    return safe;
  }

  async updateUser(
    userId: string,
    input: UpdateUserInput,
    actor = 'admin'
  ): Promise<Omit<User, 'passwordHash' | 'passwordHistory'>> {
    const existing = await this.repo.findById(userId);
    if (!existing) {
      throw new AppError(404, 'NOT_FOUND', 'User not found');
    }

    // Safety rule: Last active admin protection
    if (existing.role === 'ADMIN' && existing.status === 'ACTIVE') {
      const isDemoting = input.role !== undefined && input.role !== 'ADMIN';
      const isDisabling = input.status !== undefined && input.status !== 'ACTIVE';

      if (isDemoting || isDisabling) {
        const activeAdmins = await this.repo.countActiveAdmins();
        if (activeAdmins <= 1) {
          throw new AppError(
            409,
            'LAST_ADMIN_PROTECTION',
            'Cannot disable or demote the last remaining active administrator'
          );
        }
      }
    }

    // Bump token_version if role or status changes
    let tokenVersion = existing.tokenVersion;
    if (
      (input.role && input.role !== existing.role) ||
      (input.status && input.status !== existing.status)
    ) {
      tokenVersion += 1;
    }

    const updated = await this.repo.update(userId, {
      ...input,
      tokenVersion,
    });

    if (!updated) {
      throw new AppError(500, 'UPDATE_FAILED', 'Failed to update user');
    }

    await this.audit('USER_UPDATE', userId, actor, {
      previousRole: existing.role,
      newRole: updated.role,
      previousStatus: existing.status,
      newStatus: updated.status,
    });

    const { passwordHash: _, passwordHistory: __, ...safe } = updated;
    return safe;
  }

  async resetPassword(
    userId: string,
    actor = 'admin'
  ): Promise<{ temporaryPassword: string; mustChangePassword: true }> {
    const existing = await this.repo.findById(userId);
    if (!existing) {
      throw new AppError(404, 'NOT_FOUND', 'User not found');
    }

    const temporaryPassword = `TempPass!_${crypto.randomBytes(8).toString('base64url')}2026`;
    const newHash = await hashPassword(temporaryPassword);

    await this.repo.update(userId, {
      passwordHash: newHash,
      mustChangePassword: true,
      tokenVersion: existing.tokenVersion + 1,
    });

    await this.audit('PASSWORD_RESET_BY_ADMIN', userId, actor);

    return {
      temporaryPassword,
      mustChangePassword: true,
    };
  }

  async disableUser(userId: string, actor = 'admin'): Promise<void> {
    const existing = await this.repo.findById(userId);
    if (!existing) {
      throw new AppError(404, 'NOT_FOUND', 'User not found');
    }

    if (existing.role === 'ADMIN' && existing.status === 'ACTIVE') {
      const activeAdmins = await this.repo.countActiveAdmins();
      if (activeAdmins <= 1) {
        throw new AppError(
          409,
          'LAST_ADMIN_PROTECTION',
          'Cannot disable the last remaining active administrator'
        );
      }
    }

    await this.repo.update(userId, {
      status: 'DISABLED',
      tokenVersion: existing.tokenVersion + 1,
    });

    await this.audit('USER_DISABLE', userId, actor);
  }

  async deleteUser(userId: string, actor = 'admin'): Promise<boolean> {
    const existing = await this.repo.findById(userId);
    if (!existing) {
      throw new AppError(404, 'NOT_FOUND', 'User not found');
    }

    if (existing.role === 'ADMIN' && existing.status === 'ACTIVE') {
      const activeAdmins = await this.repo.countActiveAdmins();
      if (activeAdmins <= 1) {
        throw new AppError(
          409,
          'LAST_ADMIN_PROTECTION',
          'Cannot delete the last remaining active administrator'
        );
      }
    }

    const deleted = await this.repo.delete(userId);
    if (deleted) {
      await this.audit('USER_DELETE', userId, actor);
    }
    return deleted;
  }
}
