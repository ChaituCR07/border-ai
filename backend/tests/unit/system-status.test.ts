import { describe, it, expect, beforeEach } from 'vitest';
import { getSystemStatus, resetSystemStatusCache, type SystemStatusDeps } from '../../src/modules/system/systemStatus.js';

describe('System Status Service', () => {
  beforeEach(() => {
    resetSystemStatusCache();
  });

  it('reports DOWN when PostgreSQL fails', async () => {
    const mockPool = {
      query: async () => {
        throw new Error('Connection refused');
      },
    } as any;

    const res = await getSystemStatus({ pool: mockPool });
    expect(res.status).toBe('DOWN');
    expect(res.components.postgres.ok).toBe(false);
  });

  it('reports DEGRADED when engine status is missing from Redis', async () => {
    const mockRedis = {
      ping: async () => 'PONG',
      get: async (key: string) => {
        if (key === 'engine:status') return null;
        if (key.startsWith('camera:status:')) {
          return JSON.stringify({ state: 'ONLINE', fps: 25.0 });
        }
        return null;
      },
      xlen: async () => 0,
    } as any;

    const res = await getSystemStatus({ redis: mockRedis });
    expect(res.status).toBe('DEGRADED');
    expect(res.components.engine.ok).toBe(false);
  });

  it('reports OK when engine, cameras, postgres and redis are healthy', async () => {
    const mockPool = {
      query: async () => ({ rows: [] }),
    } as any;

    const mockRedis = {
      ping: async () => 'PONG',
      get: async (key: string) => {
        if (key === 'engine:status') {
          return JSON.stringify({ build: 'v0.3-week3', device: 'mps', at: new Date().toISOString() });
        }
        if (key.startsWith('camera:status:')) {
          return JSON.stringify({ state: 'ONLINE', fps: 25.0 });
        }
        return null;
      },
      xlen: async () => 0,
    } as any;

    const res = await getSystemStatus({ pool: mockPool, redis: mockRedis });
    expect(res.status).toBe('OK');
    expect(res.components.postgres.ok).toBe(true);
    expect(res.components.redis.ok).toBe(true);
    expect(res.components.engine.ok).toBe(true);
    expect(res.cameras.every(c => c.state === 'ONLINE')).toBe(true);
  });

  it('marks camera as OFFLINE when key is missing in Redis', async () => {
    const mockRedis = {
      ping: async () => 'PONG',
      get: async (key: string) => {
        if (key === 'engine:status') {
          return JSON.stringify({ build: 'v0.3-week3', device: 'cpu', at: new Date().toISOString() });
        }
        // missing key for cameras
        return null;
      },
      xlen: async () => 0,
    } as any;

    const res = await getSystemStatus({ redis: mockRedis });
    expect(res.status).toBe('DEGRADED');
    expect(res.cameras[0].state).toBe('OFFLINE');
  });
});
