import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';

describe('Investigation Suggest route (GET /api/investigation/suggest)', () => {
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
        plate: 'KA01XY9999',
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
        person_id: 'PERSON-0042',
        metadata: {
          person_id: 'PERSON-0042',
        },
      },
    ]);
  });

  it('suggests plates matching prefix with frequency count', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/suggest?kind=plate&prefix=KA01',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(2);
    expect(body.data.map((x: any) => x.value)).toContain('KA01AB1234');
    expect(body.data.map((x: any) => x.value)).toContain('KA01XY9999');
  });

  it('suggests cameras matching prefix', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/suggest?kind=camera&prefix=CAM',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(3);
  });

  it('suggests person identifiers for privileged roles', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/suggest?kind=person&prefix=PER',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(1);
    expect(body.data[0].value).toBe('PERSON-0042');
  });
});
