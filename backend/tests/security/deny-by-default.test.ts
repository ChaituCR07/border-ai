import { describe, it, expect } from 'vitest';
import Fastify from 'fastify';
import { onRouteSecurityGuard, preHandlerAuthGuard } from '../../src/security/route-guard.js';
import { signAccessToken } from '../../src/security/jwt.js';

describe('RBAC Deny-by-Default Architecture', () => {
  it('throws an error at startup if a route lacks security config', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);

    expect(() => {
      app.get('/unprotected-endpoint', async () => ({ hello: 'world' }));
    }).toThrowError(/deny-by-default violation/i);
  });

  it('allows startup when route declares config.public = true', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);

    expect(() => {
      app.get('/public-endpoint', { config: { public: true } }, async () => ({ hello: 'world' }));
    }).not.toThrow();
  });

  it('allows startup when route declares a valid permission', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);

    expect(() => {
      app.get('/alerts', { config: { permission: 'alerts:view' } }, async () => ({ alerts: [] }));
    }).not.toThrow();
  });

  it('throws an error at startup if route declares an unrecognized permission', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);

    expect(() => {
      app.get('/invalid-perm', { config: { permission: 'invalid:permission' as any } }, async () => ({}));
    }).toThrowError(/invalid permission/i);
  });

  it('enforces 401 when anonymous request accesses protected endpoint', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);
    app.addHook('preHandler', preHandlerAuthGuard);

    app.get('/cameras', { config: { permission: 'cameras:view' } }, async () => ({ cameras: [] }));

    const origEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production';
    try {
      const res = await app.inject({
        method: 'GET',
        url: '/cameras',
      });
      expect(res.statusCode).toBe(401);
    } finally {
      process.env.NODE_ENV = origEnv;
    }
  });

  it('enforces 403 when role lacks required permission', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);
    app.addHook('preHandler', preHandlerAuthGuard);

    // Watchlist write requires watchlist:write (Investigator or Admin)
    app.post('/watchlist', { config: { permission: 'watchlist:write' } }, async () => ({ success: true }));

    // Sign a token for a VIEWER
    const viewerToken = signAccessToken({
      userId: 'usr-viewer-1',
      role: 'VIEWER',
      sessionId: 'ses-1',
      tokenVersion: 1,
    });

    const res = await app.inject({
      method: 'POST',
      url: '/watchlist',
      headers: {
        authorization: `Bearer ${viewerToken}`,
      },
    });

    expect(res.statusCode).toBe(403);
    const body = JSON.parse(res.body);
    expect(body.error).toMatch(/Forbidden/i);
  });

  it('allows access when role possesses required permission', async () => {
    const app = Fastify();
    app.addHook('onRoute', onRouteSecurityGuard);
    app.addHook('preHandler', preHandlerAuthGuard);

    app.post('/watchlist', { config: { permission: 'watchlist:write' } }, async () => ({ success: true }));

    // Sign a token for an INVESTIGATOR
    const investigatorToken = signAccessToken({
      userId: 'usr-inv-1',
      role: 'INVESTIGATOR',
      sessionId: 'ses-2',
      tokenVersion: 1,
    });

    const res = await app.inject({
      method: 'POST',
      url: '/watchlist',
      headers: {
        authorization: `Bearer ${investigatorToken}`,
      },
    });

    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.body);
    expect(body.success).toBe(true);
  });
});
