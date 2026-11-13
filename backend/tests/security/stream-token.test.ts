import { describe, it, expect, beforeAll } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import { signAccessToken } from '../../src/security/jwt.js';

describe('Stream Token Endpoint (/api/streams/token)', () => {
  let app: FastifyInstance;
  let operatorToken: string;

  beforeAll(async () => {
    const res = await createTestApp();
    app = res.app;

    operatorToken = signAccessToken({
      userId: 'usr-op-stream',
      role: 'OPERATOR',
      sessionId: 'ses-stream-1',
      tokenVersion: 1,
    });
  });

  it('generates an EdDSA stream token bound to camera and user', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/streams/token',
      headers: {
        authorization: `Bearer ${operatorToken}`,
      },
      payload: {
        camera_id: 'cam-gate-01',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.token).toBeDefined();
    expect(body.expires_in).toBe(60);
    expect(body.max_duration_s).toBe(900);
    expect(body.url).toContain('/cam/cam-gate-01.mjpg?token=');

    // Decode token segments
    const [h, p, s] = body.token.split('.');
    const header = JSON.parse(Buffer.from(h, 'base64url').toString('utf-8'));
    const payload = JSON.parse(Buffer.from(p, 'base64url').toString('utf-8'));

    expect(header.alg).toBe('EdDSA');
    expect(header.typ).toBe('stream+jwt');
    expect(payload.aud).toBe('border-ai-stream');
    expect(payload.cam).toBe('cam-gate-01');
    expect(payload.sub).toBe('usr-op-stream');
  });

  it('rejects requests without live:view permission (anonymous)', async () => {
    const origEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production';
    try {
      const res = await app.inject({
        method: 'POST',
        url: '/api/streams/token',
        payload: {
          camera_id: 'cam-gate-01',
        },
      });
      expect(res.statusCode).toBe(401);
    } finally {
      process.env.NODE_ENV = origEnv;
    }
  });
});
