import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import { MemoryCorrelationRepo } from '../../src/modules/correlation/repo.memory.js';

describe('GET /api/topology', () => {
  let app: FastifyInstance;
  let correlationRepo: MemoryCorrelationRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    correlationRepo = res.correlationRepo;
  });

  it('returns cameras with schematic coordinates and stable version', async () => {
    const response = await app.inject({
      method: 'GET',
      url: '/api/topology',
      headers: {
        'x-user-role': 'operator',
        'x-user-id': 'op-1',
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toHaveProperty('version');
    expect(typeof body.version).toBe('string');
    expect(body.version.length).toBe(10);
    expect(body).toHaveProperty('cameras');
    expect(body).toHaveProperty('links');
    expect(Array.isArray(body.cameras)).toBe(true);
    expect(Array.isArray(body.links)).toBe(true);

    if (body.cameras.length > 0) {
      const cam = body.cameras[0];
      expect(cam).toHaveProperty('camera_id');
      expect(cam).toHaveProperty('map_x');
      expect(cam).toHaveProperty('map_y');
      expect(typeof cam.map_x).toBe('number');
      expect(typeof cam.map_y).toBe('number');
    }
  });

  it('reflects updated seeded topology', async () => {
    await correlationRepo.seedTopology(
      {
        'CAM-TEST-1': { map_x: 20, map_y: 30, name: 'Test Cam 1', location_label: 'Gate 1' },
        'CAM-TEST-2': { map_x: 40, map_y: 60, name: 'Test Cam 2', location_label: 'Gate 2' },
      },
      [
        { a: 'CAM-TEST-1', b: 'CAM-TEST-2', min_s: 50, typical_s: 100, max_s: 200, direction: 'both' },
      ]
    );

    const response = await app.inject({
      method: 'GET',
      url: '/api/topology',
      headers: {
        'x-user-role': 'viewer',
        'x-user-id': 'view-1',
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.cameras).toHaveLength(2);
    expect(body.cameras[0].camera_id).toBe('CAM-TEST-1');
    expect(body.cameras[0].map_x).toBe(20);
    expect(body.cameras[0].map_y).toBe(30);
    expect(body.links).toHaveLength(1);
    expect(body.links[0].a).toBe('CAM-TEST-1');
    expect(body.links[0].b).toBe('CAM-TEST-2');
  });
});
