import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';

describe('Journey route GET /api/investigation/journey', () => {
  let app: FastifyInstance;
  let repo: InMemoryInvestigationRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.investigationRepo;

    // Seed events for vehicle journey
    await repo.seed([
      {
        event_id: 'e1',
        camera_id: 'CAM-03',
        event_type: 'VEHICLE_DETECTED',
        track_id: '1',
        severity: 'MEDIUM',
        threat_score: 50,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
      {
        event_id: 'e2',
        camera_id: 'CAM-03',
        event_type: 'ANPR_MATCH',
        track_id: '1',
        severity: 'HIGH',
        threat_score: 75,
        timestamp: '2026-10-25T10:00:10.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
      {
        event_id: 'e3',
        camera_id: 'CAM-04',
        event_type: 'VEHICLE_DETECTED',
        track_id: '2',
        severity: 'HIGH',
        threat_score: 60,
        timestamp: '2026-10-25T10:00:38.000000Z',
        snapshot_path: null,
        plate: 'KA0IAB1234', // lookalike
        vehicle_id: 'VEH-100',
      },
      {
        event_id: 'e4',
        camera_id: 'CAM-05',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        track_id: '3',
        severity: 'CRITICAL',
        threat_score: 90,
        timestamp: '2026-10-25T10:01:50.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
    ]);
  });

  it('rejects request with neither plate nor vehicle_id with 400', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey',
    });
    expect(res.statusCode).toBe(400);
  });

  it('rejects request with both plate and vehicle_id with 400', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&vehicle_id=VEH-100',
    });
    expect(res.statusCode).toBe(400);
  });

  it('rejects request with time span > 7 days with 400', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-01T00:00:00.000Z&to=2026-10-10T00:00:00.000Z',
    });
    expect(res.statusCode).toBe(400);
    const body = res.json();
    expect(body.error.message).toContain('7 days');
  });

  it('returns vehicle journey matching plate and lookalikes', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.total_events).toBe(4);
    expect(body.data.sightings).toHaveLength(3);
    expect(body.data.sightings.map((s: any) => s.camera_id)).toEqual(['CAM-03', 'CAM-04', 'CAM-05']);
    expect(body.data.transitions).toEqual([
      { from: 'CAM-03', to: 'CAM-04', gap_s: 28 },
      { from: 'CAM-04', to: 'CAM-05', gap_s: 72 },
    ]);
    expect(body.data.plate_variants).toEqual(['KA01AB1234', 'KA0IAB1234']);
    expect(body.meta.truncated).toBe(false);
  });

  it('returns vehicle journey by vehicle_id', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?vehicle_id=VEH-100&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.total_events).toBe(4);
    expect(body.data.sightings).toHaveLength(3);
  });
});
