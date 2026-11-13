import { IUsersRepo } from '../users/users.repo.js';
import { SessionService } from './sessions.js';
import {
  hashPassword,
  verifyOrDummy,
  verifyPassword,
  validatePassword,
  needsRehash,
} from '../../security/passwords.js';
import { signAccessToken, ACCESS_TOKEN_TTL_SECONDS } from '../../security/jwt.js';
import { authThrottle } from '../../security/throttle.js';
import { ROLE_PERMISSIONS, Permission } from '../../security/policy.js';
import { AppError } from '../../common/errors.js';
import { User } from '../users/users.types.js';

export interface LoginResult {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: {
    userId: string;
    username: string;
    displayName: string | null;
    role: User['role'];
    mustChangePassword: boolean;
  };
}

export interface RefreshResult {
  accessToken: string;
  refreshToken?: string;
  expiresIn: number;
  user: {
    userId: string;
    username: string;
    displayName: string | null;
    role: User['role'];
    mustChangePassword: boolean;
  };
}

export interface AuditSink {
  log(entry: {
    actor: string;
    action: string;
    entityType: string;
    entityId: string;
    role?: string;
    ip?: string;
    userAgent?: string;
    detail?: Record<string, any>;
  }): Promise<void>;
}

export class AuthService {
  constructor(
    private usersRepo: IUsersRepo,
    private sessionService: SessionService,
    private auditSink?: AuditSink
  ) {}

  private async audit(action: string, entityId: string, actor = 'anonymous', role?: string, detail?: Record<string, any>) {
    if (this.auditSink) {
      try {
        await this.auditSink.log({
          actor,
          action,
          entityType: 'AUTH',
          entityId,
          role,
          detail,
        });
      } catch (err: any) {
        console.warn(`[auth] Audit log failed: ${err.message}`);
      }
    }
  }

  async login(
    usernameInput: string,
    passwordInput: string,
    meta?: { ip?: string; userAgent?: string }
  ): Promise<LoginResult> {
    const username = usernameInput.trim();
    const acctKey = `acct:${username.toLowerCase()}`;
    const ipKey = meta?.ip ? `ip:${meta.ip}` : null;

    // 1. Check throttling on account and IP
    const acctThrottle = authThrottle.check(acctKey);
    if (acctThrottle.blocked) {
      throw new AppError(
        429,
        'TOO_MANY_REQUESTS',
        `Account is temporarily throttled due to multiple failed login attempts. Retry after ${acctThrottle.retryAfterSeconds}s.`
      );
    }

    if (ipKey) {
      const ipThrottle = authThrottle.check(ipKey);
      if (ipThrottle.blocked) {
        throw new AppError(
          429,
          'TOO_MANY_REQUESTS',
          `IP address is temporarily throttled. Retry after ${ipThrottle.retryAfterSeconds}s.`
        );
      }
    }

    // 2. Fetch user
    const user = await this.usersRepo.findByUsername(username);

    // 3. Verify password or dummy hash (anti-enumeration)
    const isValid = await verifyOrDummy(user?.passwordHash, passwordInput);

    if (!user || !isValid || user.status !== 'ACTIVE') {
      authThrottle.recordFailure(acctKey);
      if (ipKey) authThrottle.recordFailure(ipKey);

      await this.audit(
        'LOGIN_FAILURE',
        user?.userId ?? 'unknown',
        username,
        user?.role,
        {
          reason: !user ? 'unknown_user' : !isValid ? 'bad_password' : 'disabled_account',
          ip: meta?.ip,
        }
      );

      // Uniform error message across all failures
      throw new AppError(401, 'INVALID_CREDENTIALS', 'Invalid username or password');
    }

    // 4. Successful login: reset throttling
    authThrottle.reset(acctKey);
    if (ipKey) authThrottle.reset(ipKey);

    // 5. Automatic parameter rehash if baseline was upgraded
    if (needsRehash(user.passwordHash)) {
      try {
        const upgradedHash = await hashPassword(passwordInput);
        await this.usersRepo.update(user.userId, { passwordHash: upgradedHash });
      } catch (err: any) {
        console.warn(`[auth] Rehash failed: ${err.message}`);
      }
    }

    // Update last login
    await this.usersRepo.update(user.userId, {
      failedAttempts: 0,
      lastLoginAt: new Date(),
    });

    // 6. Create session and tokens
    const { session, refreshToken } = await this.sessionService.createSession({
      userId: user.userId,
      ip: meta?.ip,
      userAgent: meta?.userAgent,
    });

    const accessToken = signAccessToken({
      userId: user.userId,
      role: user.role,
      sessionId: session.sessionId,
      tokenVersion: user.tokenVersion,
    });

    await this.audit('LOGIN_SUCCESS', user.userId, user.username, user.role, {
      sessionId: session.sessionId,
      ip: meta?.ip,
    });

    return {
      accessToken,
      refreshToken,
      expiresIn: ACCESS_TOKEN_TTL_SECONDS,
      user: {
        userId: user.userId,
        username: user.username,
        displayName: user.displayName ?? null,
        role: user.role,
        mustChangePassword: user.mustChangePassword,
      },
    };
  }

  async refresh(
    rawRefreshToken: string,
    meta?: { ip?: string; userAgent?: string }
  ): Promise<RefreshResult> {
    const rotation = await this.sessionService.rotateRefreshToken(rawRefreshToken, meta);

    if (!rotation.success) {
      if (rotation.reason === 'REUSE_DETECTED') {
        await this.audit('REFRESH_REUSE_DETECTED', 'unknown', 'system', undefined, {
          ip: meta?.ip,
        });
      }
      throw new AppError(401, 'INVALID_REFRESH_TOKEN', 'Session expired or refresh token invalid');
    }

    const user = await this.usersRepo.findById(rotation.session.userId);
    if (!user || user.status !== 'ACTIVE') {
      throw new AppError(401, 'INVALID_REFRESH_TOKEN', 'User account is inactive or disabled');
    }

    const accessToken = signAccessToken({
      userId: user.userId,
      role: user.role,
      sessionId: rotation.session.sessionId,
      tokenVersion: user.tokenVersion,
    });

    return {
      accessToken,
      refreshToken: rotation.refreshToken, // undefined when in multi-tab grace window
      expiresIn: ACCESS_TOKEN_TTL_SECONDS,
      user: {
        userId: user.userId,
        username: user.username,
        displayName: user.displayName ?? null,
        role: user.role,
        mustChangePassword: user.mustChangePassword,
      },
    };
  }

  async logout(sessionId: string, actor = 'unknown'): Promise<void> {
    await this.sessionService.revokeSession(sessionId, 'LOGOUT');
    await this.audit('LOGOUT', sessionId, actor);
  }

  async logoutAll(userId: string, actor = 'unknown'): Promise<void> {
    const user = await this.usersRepo.findById(userId);
    if (user) {
      await this.usersRepo.update(userId, { tokenVersion: user.tokenVersion + 1 });
    }
    await this.sessionService.revokeAllUserSessions(userId, 'LOGOUT_ALL');
    await this.audit('LOGOUT_ALL', userId, actor);
  }

  async changePassword(
    userId: string,
    currentPasswordInput: string,
    newPasswordInput: string
  ): Promise<void> {
    const user = await this.usersRepo.findById(userId);
    if (!user) {
      throw new AppError(404, 'NOT_FOUND', 'User not found');
    }

    // Verify current password
    const validCurrent = await verifyPassword(user.passwordHash, currentPasswordInput);
    if (!validCurrent) {
      throw new AppError(401, 'INVALID_CREDENTIALS', 'Current password is incorrect');
    }

    // Validate new password policy
    const policy = await validatePassword(newPasswordInput, {
      username: user.username,
      email: user.email ?? undefined,
      history: user.passwordHistory,
    });

    if (!policy.valid) {
      throw new AppError(400, 'PASSWORD_POLICY_VIOLATION', policy.errors.join(', '));
    }

    // Hash new password
    const newHash = await hashPassword(newPasswordInput);
    const updatedHistory = [newHash, ...user.passwordHistory].slice(0, 5);

    // Bump token_version to invalidate prior access tokens and revoke prior sessions
    await this.usersRepo.update(userId, {
      passwordHash: newHash,
      passwordHistory: updatedHistory,
      mustChangePassword: false,
      tokenVersion: user.tokenVersion + 1,
    });

    await this.sessionService.revokeAllUserSessions(userId, 'PASSWORD_CHANGE');
    await this.audit('PASSWORD_CHANGE', userId, user.username, user.role);
  }

  async getMe(userId: string) {
    const user = await this.usersRepo.findById(userId);
    if (!user) {
      throw new AppError(404, 'NOT_FOUND', 'User not found');
    }

    const permissions = Array.from(ROLE_PERMISSIONS[user.role] ?? []);

    return {
      userId: user.userId,
      username: user.username,
      email: user.email ?? null,
      displayName: user.displayName ?? null,
      role: user.role,
      mustChangePassword: user.mustChangePassword,
      permissions,
    };
  }
}
