import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';

describe('Investigation Facets route (GET /api/investigation/facets)', () => {
  let app: FastifyInstance;
  let repo: InMemoryInvestigationRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.investigationRepo;

    await repo.seed([
      {
        event_id: '11111111-1111-1111-1111-111111111111',
        camera_id: 'CAM-01',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        track_id: '42',
        severity: 'CRITICAL',
        threat_score: 95,
        timestamp: '2026-10-25T02:15:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        metadata: {},
      },
      {
        event_id: '22222222-2222-2222-2222-222222222222',
        camera_id: 'CAM-02',
        event_type: 'VEHICLE_DETECTED',
        track_id: '43',
        severity: 'HIGH',
        threat_score: 80,
        timestamp: '2026-10-25T02:16:00.000000Z',
        snapshot_path: null,
        plate: 'KA0IAB1234',
        metadata: {},
      },
      {
        event_id: '33333333-3333-3333-3333-333333333333',
        camera_id: 'CAM-03',
        event_type: 'PERSON_DETECTED',
        track_id: '44',
        severity: 'LOW',
        threat_score: 15,
        timestamp: '2026-10-25T02:20:00.000000Z',
        snapshot_path: null,
        metadata: {},
      },
    ]);
  });

  it('returns facet counts across dimensions for unfiltered query', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/facets',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.total).toBe(3);
    expect(body.data.by_camera.length).toBe(3);
    expect(body.data.by_severity.CRITICAL).toBe(1);
    expect(body.data.by_severity.HIGH).toBe(1);
    expect(body.data.by_severity.LOW).toBe(1);
    expect(body.data.score_histogram.length).toBe(10);
    expect(body.data.hours.length).toBe(24);
    expect(body.meta.capped).toBe(false);
  });

  it('demonstrates disjunctive facets: selecting CAM-01 preserves other cameras in by_camera', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/facets?camera_id=CAM-01',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    // Matching total is 1 (only CAM-01)
    expect(body.data.total).toBe(1);

    // Disjunctive facet: by_camera still shows all 3 cameras so facet counts do not collapse (ADR 0025)
    expect(body.data.by_camera.length).toBe(3);
    const cam01 = body.data.by_camera.find((c: any) => c.value === 'CAM-01');
    const cam02 = body.data.by_camera.find((c: any) => c.value === 'CAM-02');
    expect(cam01.count).toBe(1);
    expect(cam02.count).toBe(1);
  });
});
