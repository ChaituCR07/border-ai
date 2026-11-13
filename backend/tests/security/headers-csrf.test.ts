import { describe, it, expect, beforeAll } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';

describe('Security Headers, CORS & CSRF Defense', () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    const res = await createTestApp();
    app = res.app;
  });

  describe('Security Headers', () => {
    it('returns strict security headers on API responses', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/health',
      });

      expect(res.headers['x-content-type-options']).toBe('nosniff');
      expect(res.headers['x-frame-options']).toBe('DENY');
      expect(res.headers['referrer-policy']).toBe('strict-origin-when-cross-origin');
      expect(res.headers['permissions-policy']).toContain('camera=()');
      expect(res.headers['cross-origin-opener-policy']).toBe('same-origin');
      expect(res.headers['cross-origin-resource-policy']).toBe('same-origin');
      expect(res.headers['content-security-policy']).toContain("default-src 'self'");
    });
  });

  describe('CORS Allow-List', () => {
    it('allows permitted origin', async () => {
      const res = await app.inject({
        method: 'OPTIONS',
        url: '/health',
        headers: {
          origin: 'http://localhost:5173',
          'access-control-request-method': 'GET',
        },
      });

      expect(res.headers['access-control-allow-origin']).toBe('http://localhost:5173');
      expect(res.headers['access-control-allow-credentials']).toBe('true');
    });

    it('denies disallowed origin', async () => {
      const res = await app.inject({
        method: 'OPTIONS',
        url: '/health',
        headers: {
          origin: 'http://evil-site.com',
          'access-control-request-method': 'GET',
        },
      });

      expect(res.headers['access-control-allow-origin']).toBeUndefined();
    });
  });

  describe('CSRF Protection for Cookie Auth Endpoints', () => {
    it('blocks cross-site fetch to /api/auth/refresh', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/refresh',
        headers: {
          'sec-fetch-site': 'cross-site',
        },
        payload: {},
      });

      expect(res.statusCode).toBe(403);
      expect(res.json().message).toContain('CSRF validation failed');
    });

    it('blocks cookie refresh when missing CSRF token', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/refresh',
        headers: {
          cookie: 'refresh_token=sample_rt_cookie_123',
          'sec-fetch-mode': 'navigate',
        },
        payload: {},
      });

      expect(res.statusCode).toBe(403);
      expect(res.json().message).toContain('missing X-CSRF-Token header');
    });

    it('permits request with X-CSRF-Token header', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/auth/refresh',
        headers: {
          cookie: 'refresh_token=sample_rt_cookie_123',
          'x-csrf-token': 'valid-csrf-token',
        },
        payload: {},
      });

      // Passes CSRF guard, fails inside route because refresh_token is invalid dummy string (401, not 403 CSRF!)
      expect(res.statusCode).toBe(401);
    });
  });
});
