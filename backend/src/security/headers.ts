import type { FastifyPluginAsync, FastifyReply, FastifyRequest } from 'fastify';
import fp from 'fastify-plugin';

export const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "connect-src 'self' ws: wss:",
  "font-src 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ');

export const PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=()';

export interface SecurityHeadersOptions {
  enableCsp?: boolean;
}

/**
 * Hook to apply strict production-grade security headers to all HTTP responses
 */
export async function applySecurityHeaders(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  reply.header('X-Content-Type-Options', 'nosniff');
  reply.header('X-Frame-Options', 'DENY');
  reply.header('Referrer-Policy', 'strict-origin-when-cross-origin');
  reply.header('Permissions-Policy', PERMISSIONS_POLICY);
  reply.header('Cross-Origin-Opener-Policy', 'same-origin');
  reply.header('Cross-Origin-Resource-Policy', 'same-origin');
  
  // Swagger UI requires inline styles/scripts, so we apply CSP everywhere except OpenAPI docs
  if (!request.url.startsWith('/docs') && !request.url.startsWith('/openapi.json')) {
    reply.header('Content-Security-Policy', CONTENT_SECURITY_POLICY);
  }
}

/**
 * Validates CSRF token or Sec-Fetch-Site for state-changing or cookie-bearing auth endpoints
 */
export async function csrfProtectionGuard(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  // Only apply to /api/auth/refresh and /api/auth/logout
  if (!request.url.startsWith('/api/auth/refresh') && !request.url.startsWith('/api/auth/logout')) {
    return;
  }

  // 1. Modern browser Sec-Fetch-Site defense
  const secFetchSite = request.headers['sec-fetch-site'];
  if (secFetchSite === 'cross-site') {
    return reply.status(403).send({
      statusCode: 403,
      error: 'Forbidden',
      message: 'CSRF validation failed: cross-site request rejected',
    });
  }

  // 2. Cookie check: if refresh_token is sent in cookie, verify double-submit CSRF token or custom header
  const cookies = request.headers.cookie;
  if (cookies && cookies.includes('refresh_token=')) {
    const csrfHeader = request.headers['x-csrf-token'];
    const origin = request.headers['origin'];
    const secFetchMode = request.headers['sec-fetch-mode'];

    // In browsers, fetch/XHR requests to same-origin or CORS allowed origins send either Origin or X-Requested-With / X-CSRF-Token
    // If neither CSRF header nor same-origin is indicated, reject
    if (!csrfHeader && (!secFetchMode || secFetchMode === 'navigate')) {
      return reply.status(403).send({
        statusCode: 403,
        error: 'Forbidden',
        message: 'CSRF validation failed: missing X-CSRF-Token header for cookie authentication',
      });
    }
  }
}
