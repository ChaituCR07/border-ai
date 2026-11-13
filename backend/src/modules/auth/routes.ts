import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { AuthService } from './service.js';
import { LoginSchema, ChangePasswordSchema } from './schemas.js';
import { keyManager } from '../../security/keys.js';
import { AppError } from '../../common/errors.js';

const REFRESH_COOKIE_NAME = 'border_ai_refresh';

function parseCookies(cookieHeader?: string): Record<string, string> {
  const cookies: Record<string, string> = {};
  if (!cookieHeader) return cookies;
  for (const pair of cookieHeader.split(';')) {
    const [key, val] = pair.trim().split('=');
    if (key && val) {
      cookies[key.trim()] = decodeURIComponent(val.trim());
    }
  }
  return cookies;
}

function setRefreshCookie(reply: FastifyReply, token: string, maxAgeSeconds: number) {
  const secure = process.env.COOKIE_SECURE === 'true' || process.env.NODE_ENV === 'production';
  const parts = [
    `${REFRESH_COOKIE_NAME}=${encodeURIComponent(token)}`,
    'HttpOnly',
    'SameSite=Strict',
    'Path=/api/auth',
    `Max-Age=${maxAgeSeconds}`,
  ];
  if (secure) parts.push('Secure');

  reply.header('Set-Cookie', parts.join('; '));
}

function clearRefreshCookie(reply: FastifyReply) {
  const secure = process.env.COOKIE_SECURE === 'true' || process.env.NODE_ENV === 'production';
  const parts = [
    `${REFRESH_COOKIE_NAME}=`,
    'HttpOnly',
    'SameSite=Strict',
    'Path=/api/auth',
    'Max-Age=0',
    'Expires=Thu, 01 Jan 1970 00:00:00 GMT',
  ];
  if (secure) parts.push('Secure');

  reply.header('Set-Cookie', parts.join('; '));
}

export function registerAuthRoutes(app: FastifyInstance, authService: AuthService) {
  // Public JWKS endpoint
  app.get(
    '/.well-known/jwks.json',
    {
      config: { public: true },
    },
    async (_req, reply) => {
      reply.header('Cache-Control', 'public, max-age=300');
      return keyManager.getJwks();
    }
  );

  // POST /api/auth/login
  app.post(
    '/api/auth/login',
    {
      config: { public: true },
    },
    async (req: FastifyRequest, reply: FastifyReply) => {
      const parsed = LoginSchema.safeParse(req.body);
      if (!parsed.success) {
        throw new AppError(400, 'VALIDATION_ERROR', parsed.error.errors[0]?.message ?? 'Invalid payload');
      }

      const ip = (req.headers['x-forwarded-for'] as string) || req.ip;
      const userAgent = req.headers['user-agent'];

      const result = await authService.login(parsed.data.username, parsed.data.password, {
        ip,
        userAgent,
      });

      // 8 hours cookie max age
      setRefreshCookie(reply, result.refreshToken, 8 * 3600);

      reply.header('Cache-Control', 'no-store');
      return {
        accessToken: result.accessToken,
        expiresIn: result.expiresIn,
        user: result.user,
      };
    }
  );

  // POST /api/auth/refresh
  app.post(
    '/api/auth/refresh',
    {
      config: { public: true },
    },
    async (req: FastifyRequest, reply: FastifyReply) => {
      // CSRF Defense for cookie endpoints: Custom header or origin check
      const csrfHeader = req.headers['x-csrf-token'] || req.headers['x-requested-with'];
      const origin = req.headers['origin'];
      if (!csrfHeader && !origin) {
        // Enforce custom header or origin header
        throw new AppError(403, 'CSRF_BLOCKED', 'Missing required CSRF defense headers');
      }

      const cookies = parseCookies(req.headers['cookie']);
      const refreshToken = cookies[REFRESH_COOKIE_NAME];

      if (!refreshToken) {
        throw new AppError(401, 'MISSING_REFRESH_TOKEN', 'No refresh token cookie found');
      }

      const ip = (req.headers['x-forwarded-for'] as string) || req.ip;
      const userAgent = req.headers['user-agent'];

      const result = await authService.refresh(refreshToken, { ip, userAgent });

      if (result.refreshToken) {
        setRefreshCookie(reply, result.refreshToken, 8 * 3600);
      }

      reply.header('Cache-Control', 'no-store');
      return {
        accessToken: result.accessToken,
        expiresIn: result.expiresIn,
        user: result.user,
      };
    }
  );

  // POST /api/auth/logout
  app.post(
    '/api/auth/logout',
    {
      config: { permission: 'system:status' },
    },
    async (req: FastifyRequest, reply: FastifyReply) => {
      const sessionId = (req.actor as any)?.sid;
      if (sessionId) {
        await authService.logout(sessionId, req.actor?.id);
      }
      clearRefreshCookie(reply);
      return { success: true, message: 'Logged out successfully' };
    }
  );

  // POST /api/auth/logout-all
  app.post(
    '/api/auth/logout-all',
    {
      config: { permission: 'system:status' },
    },
    async (req: FastifyRequest, reply: FastifyReply) => {
      const userId = req.actor?.id;
      if (userId) {
        await authService.logoutAll(userId, req.actor?.id);
      }
      clearRefreshCookie(reply);
      return { success: true, message: 'All active sessions revoked' };
    }
  );

  // GET /api/auth/me
  app.get(
    '/api/auth/me',
    {
      config: { permission: 'system:status' },
    },
    async (req: FastifyRequest) => {
      return authService.getMe(req.actor.id);
    }
  );

  // POST /api/auth/change-password
  app.post(
    '/api/auth/change-password',
    {
      config: { permission: 'system:status' },
    },
    async (req: FastifyRequest, reply: FastifyReply) => {
      const parsed = ChangePasswordSchema.safeParse(req.body);
      if (!parsed.success) {
        throw new AppError(400, 'VALIDATION_ERROR', parsed.error.errors[0]?.message ?? 'Invalid payload');
      }

      await authService.changePassword(
        req.actor.id,
        parsed.data.currentPassword,
        parsed.data.newPassword
      );

      clearRefreshCookie(reply);
      return { success: true, message: 'Password changed successfully. Please log in again.' };
    }
  );
}
