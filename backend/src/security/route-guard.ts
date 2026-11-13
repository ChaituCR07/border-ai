import { FastifyRequest, FastifyReply, RouteOptions } from 'fastify';
import { Permission, hasPermission, PERMISSIONS } from './policy.js';
import { verifyAccessToken, AuthError, Role } from './jwt.js';
import { AppError } from '../common/errors.js';

export interface RouteSecurityConfig {
  permission?: Permission;
  public?: boolean;
}

declare module 'fastify' {
  interface FastifyContextConfig {
    permission?: Permission;
    public?: boolean;
  }
}

/**
 * Fastify onRoute hook enforcing deny-by-default architecture:
 * Every route MUST declare either `config: { public: true }` or `config: { permission: '...' }`
 */
export function onRouteSecurityGuard(routeOptions: RouteOptions) {
  const url = routeOptions.url;

  // 1. Automatically permit CORS preflight OPTIONS requests
  const isOptions =
    routeOptions.method === 'OPTIONS' ||
    (Array.isArray(routeOptions.method) && routeOptions.method.includes('OPTIONS'));

  if (isOptions) {
    if (!routeOptions.config) {
      routeOptions.config = { public: true };
    } else {
      (routeOptions.config as RouteSecurityConfig).public = true;
    }
    return;
  }

  // 2. Exclude static swagger docs assets in development
  if (url.startsWith('/docs') || url.startsWith('/swagger') || url === '/openapi.json') {
    if (!routeOptions.config) {
      routeOptions.config = { public: true };
    } else {
      (routeOptions.config as RouteSecurityConfig).public = true;
    }
    return;
  }

  const cfg = routeOptions.config as RouteSecurityConfig | undefined;
  if (!cfg?.public && !cfg?.permission) {
    throw new Error(
      `Route without security policy (deny-by-default violation): ${routeOptions.method} ${routeOptions.url}`
    );
  }

  if (cfg.permission && !PERMISSIONS.includes(cfg.permission)) {
    throw new Error(
      `Route specifies invalid permission '${cfg.permission}': ${routeOptions.method} ${routeOptions.url}`
    );
  }
}

/**
 * Global preHandler authentication and authorization guard
 */
export async function preHandlerAuthGuard(req: FastifyRequest, _reply: FastifyReply) {
  const cfg = (req.routeOptions.config || {}) as RouteSecurityConfig;

  // 1. Skip authentication if explicitly public
  if (cfg.public) {
    return;
  }

  // 2. Extract Bearer token
  const authHeader = req.headers['authorization'];
  let actorFound = false;

  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice(7).trim();
    try {
      const claims = verifyAccessToken(token);
      req.actor = {
        id: claims.sub,
        role: claims.role,
        sid: claims.sid,
      } as any;
      actorFound = true;
    } catch (err: any) {
      if (err instanceof AuthError) {
        throw new AppError(401, 'UNAUTHENTICATED', `Authentication failed: ${err.message}`);
      }
      throw new AppError(401, 'UNAUTHENTICATED', 'Invalid authentication token');
    }
  }

  // 3. Fallback for test environments (AUTH_MODE=test or x-actor-id)
  if (!actorFound) {
    if (process.env.AUTH_MODE === 'test' || process.env.NODE_ENV === 'test') {
      const actorId = (req.headers['x-actor-id'] as string) || 'test-user';
      const actorRole = ((req.headers['x-actor-role'] as string) || 'ADMIN').toUpperCase() as Role;
      req.actor = {
        id: actorId,
        role: actorRole,
      } as any;
      actorFound = true;
    }
  }

  if (!actorFound) {
    throw new AppError(401, 'UNAUTHENTICATED', 'Authentication required: missing Bearer token');
  }

  // 4. Role-Based Access Control (RBAC) permission check
  if (cfg.permission) {
    const userRole = req.actor?.role as Role;
    if (!userRole || !hasPermission(userRole, cfg.permission)) {
      throw new AppError(
        403,
        'FORBIDDEN',
        `Access denied: role '${userRole}' lacks permission '${cfg.permission}'`
      );
    }
  }
}
