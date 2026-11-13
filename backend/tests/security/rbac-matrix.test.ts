import { describe, it, expect, beforeAll } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import { signAccessToken, Role } from '../../src/security/jwt.js';

describe('RBAC Route Matrix Tests', () => {
  let app: FastifyInstance;

  const roles: Role[] = ['VIEWER', 'OPERATOR', 'INVESTIGATOR', 'ADMIN'];
  const tokens: Record<Role, string> = {} as any;

  beforeAll(async () => {
    const res = await createTestApp();
    app = res.app;

    for (const r of roles) {
      tokens[r] = signAccessToken({
        userId: `usr-${r.toLowerCase()}`,
        role: r,
        sessionId: `ses-${r.toLowerCase()}`,
        tokenVersion: 1,
      });
    }
  });

  // 1. Watchlist Write: Only Investigator and Admin permitted
  describe('Watchlist write access (/api/watchlist)', () => {
    it('denies anonymous with 401', async () => {
      const origEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      try {
        const res = await app.inject({
          method: 'POST',
          url: '/api/watchlist',
          payload: { entity_type: 'plate', plate: 'ABC1234' },
        });
        expect(res.statusCode).toBe(401);
      } finally {
        process.env.NODE_ENV = origEnv;
      }
    });

    it('denies VIEWER with 403', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/watchlist',
        headers: { authorization: `Bearer ${tokens.VIEWER}` },
        payload: { entity_type: 'plate', plate: 'ABC1234' },
      });
      expect(res.statusCode).toBe(403);
    });

    it('denies OPERATOR with 403', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/watchlist',
        headers: { authorization: `Bearer ${tokens.OPERATOR}` },
        payload: { entity_type: 'plate', plate: 'ABC1234' },
      });
      expect(res.statusCode).toBe(403);
    });

    it('permits INVESTIGATOR (not 401/403)', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/watchlist',
        headers: { authorization: `Bearer ${tokens.INVESTIGATOR}` },
        payload: { entity_type: 'plate', plate: 'ABC1234' },
      });
      expect(res.statusCode).not.toBe(401);
      expect(res.statusCode).not.toBe(403);
    });

    it('permits ADMIN (not 401/403)', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/watchlist',
        headers: { authorization: `Bearer ${tokens.ADMIN}` },
        payload: { entity_type: 'plate', plate: 'XYZ9876' },
      });
      expect(res.statusCode).not.toBe(401);
      expect(res.statusCode).not.toBe(403);
    });
  });

  // 2. Alert Acknowledge: Operator, Investigator, Admin permitted; Viewer denied
  describe('Alert Acknowledge (/api/alerts/:id/acknowledge)', () => {
    it('denies VIEWER with 403', async () => {
      const res = await app.inject({
        method: 'PATCH',
        url: '/api/alerts/alt-test-01/acknowledge',
        headers: { authorization: `Bearer ${tokens.VIEWER}` },
        payload: { acknowledged_by: 'viewer_user' },
      });
      expect(res.statusCode).toBe(403);
    });

    it('permits OPERATOR (not 401/403)', async () => {
      const res = await app.inject({
        method: 'PATCH',
        url: '/api/alerts/alt-test-01/acknowledge',
        headers: { authorization: `Bearer ${tokens.OPERATOR}` },
        payload: { acknowledged_by: 'operator_dan' },
      });
      expect(res.statusCode).not.toBe(401);
      expect(res.statusCode).not.toBe(403);
    });
  });

  // 3. User Management: Admin only
  describe('User Management (/api/users)', () => {
    it('denies VIEWER with 403', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/users',
        headers: { authorization: `Bearer ${tokens.VIEWER}` },
      });
      expect(res.statusCode).toBe(403);
    });

    it('denies OPERATOR with 403', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/users',
        headers: { authorization: `Bearer ${tokens.OPERATOR}` },
      });
      expect(res.statusCode).toBe(403);
    });

    it('denies INVESTIGATOR with 403', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/users',
        headers: { authorization: `Bearer ${tokens.INVESTIGATOR}` },
      });
      expect(res.statusCode).toBe(403);
    });

    it('permits ADMIN with 200', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/users',
        headers: { authorization: `Bearer ${tokens.ADMIN}` },
      });
      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(Array.isArray(body.data)).toBe(true);
    });
  });
});
