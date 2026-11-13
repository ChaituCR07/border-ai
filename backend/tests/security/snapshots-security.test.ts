import { describe, it, expect, beforeAll } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import { signAccessToken } from '../../src/security/jwt.js';

describe('Snapshots Security & Person Evidence Redaction', () => {
  let app: FastifyInstance;
  let viewerToken: string;
  let operatorToken: string;

  beforeAll(async () => {
    const res = await createTestApp();
    app = res.app;

    viewerToken = signAccessToken({
      userId: 'usr-viewer-snap',
      role: 'VIEWER',
      sessionId: 'ses-snap-1',
      tokenVersion: 1,
    });

    operatorToken = signAccessToken({
      userId: 'usr-op-snap',
      role: 'OPERATOR',
      sessionId: 'ses-snap-2',
      tokenVersion: 1,
    });
  });

  it('rejects path traversal attempts with 400 or 404', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/../../etc/passwd',
      headers: { authorization: `Bearer ${operatorToken}` },
    });
    expect([400, 404]).toContain(res.statusCode);
  });

  it('serves redacted placeholder to VIEWER for person evidence without 403', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/person_crop_01.jpg',
      headers: { authorization: `Bearer ${viewerToken}` },
    });

    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toContain('image/svg+xml');
    expect(res.body).toContain('[Evidence Redacted for Viewer Role]');
  });

  it('permits OPERATOR to attempt viewing real evidence file', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/vehicle_gate_01.jpg',
      headers: { authorization: `Bearer ${operatorToken}` },
    });

    // 404 because file doesn't exist on disk, not 401 or 403!
    expect(res.statusCode).toBe(404);
  });

  it('rejects anonymous access to snapshots with 401', async () => {
    const origEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production';
    try {
      const res = await app.inject({
        method: 'GET',
        url: '/api/snapshots/vehicle_gate_01.jpg',
      });
      expect(res.statusCode).toBe(401);
    } finally {
      process.env.NODE_ENV = origEnv;
    }
  });
});
