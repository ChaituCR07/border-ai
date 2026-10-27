import type { FastifyRequest } from 'fastify';
import { AppError } from './errors.js';
import type { Actor, Role } from '../types/domain.js';

declare module 'fastify' {
  interface FastifyRequest {
    actor: Actor;
  }
}

export async function authenticate(req: FastifyRequest): Promise<void> {
  // Day 15 Auth seam: development stub actor.
  // Full JWT verification, password hashing, and token parsing is scheduled for Day 26.
  if (process.env.NODE_ENV === 'production') {
    throw new AppError(
      500,
      'SECURITY_ERROR',
      'Stub authentication is forbidden in production mode. Configure real JWT verifier.'
    );
  }

  // Set default dev actor
  req.actor = {
    id: (req.headers['x-actor-id'] as string) || 'dev-operator',
    role: ((req.headers['x-actor-role'] as Role) || 'ADMIN'),
  };
}

export async function authenticateWs(req: FastifyRequest): Promise<Actor> {
  // Day 17 Auth seam: ticket / query-param dev actor verification.
  // Day 26 replaces this with short-lived ?ticket=... token exchange.
  const query = req.query as Record<string, string> | undefined;
  const id = (req.headers['x-actor-id'] as string) || query?.actor_id || 'dev-operator';
  const role = ((req.headers['x-actor-role'] as Role) || (query?.role as Role) || 'OPERATOR');
  return { id, role };
}

export function requireRole(...allowedRoles: Role[]) {
  return async (req: FastifyRequest): Promise<void> => {
    if (!req.actor) {
      throw new AppError(401, 'UNAUTHENTICATED', 'Authentication required');
    }
    if (!allowedRoles.includes(req.actor.role)) {
      throw new AppError(403, 'FORBIDDEN', `Insufficient role: requires one of [${allowedRoles.join(', ')}]`);
    }
  };
}
