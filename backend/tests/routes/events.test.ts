import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';

describe('Events routes', () => {
  let app: FastifyInstance;
  let repo: InMemoryEventsRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.eventsRepo;

    // Seed mock events
    await repo.seed([
      {
        event_id: '11111111-1111-1111-1111-111111111111',
        camera_id: 'CAM-01',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        track_id: '42',
        severity: 'CRITICAL',
        threat_score: 95,
        timestamp: '2026-10-25T02:15:00.000000Z',
        snapshot_path: 'CAM-01/snap1.jpg',
        plate: 'KA01AB1234',
        metadata: {
          explanation: { factors: [{ name: 'restricted_zone', points: 40 }] },
        },
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
        plate: 'KA0IAB1234', // OCR lookalike
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

  it('GET /api/events returns paginated list ordered by timestamp DESC', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?limit=10',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(3);
    expect(body.data[0].event_id).toBe('33333333-3333-3333-3333-333333333333');
    expect(body.meta.limit).toBe(10);
    expect(body.meta.has_more).toBe(false);
  });

  it('GET /api/events filters by plate with lookalike matching by default', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?plate=KA01AB1234',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(2);
    // Exact hit
    const exact = body.data.find((e: any) => e.plate === 'KA01AB1234');
    expect(exact?.plate_match).toBe('exact');
    // Lookalike hit
    const lookalike = body.data.find((e: any) => e.plate === 'KA0IAB1234');
    expect(lookalike?.plate_match).toBe('lookalike');
  });

  it('GET /api/events filters by plate with exact match mode', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?plate=KA01AB1234&plate_match=exact',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(1);
    expect(body.data[0].plate).toBe('KA01AB1234');
    expect(body.data[0].plate_match).toBe('exact');
  });

  it('GET /api/events supports prefix plate matching', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?plate=KA01&plate_match=prefix',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(1);
    expect(body.data[0].plate).toBe('KA01AB1234');
    expect(body.data[0].plate_match).toBe('prefix');
  });

  it('GET /api/events sorts by threat_score DESC when sort=score', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?sort=score',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(3);
    expect(body.data[0].threat_score).toBe(95);
    expect(body.data[1].threat_score).toBe(80);
    expect(body.data[2].threat_score).toBe(15);
  });

  it('GET /api/events routes omnibox q free text automatically', async () => {
    // q as plate
    const plateRes = await app.inject({
      method: 'GET',
      url: '/api/events?q=KA01AB1234',
    });
    expect(plateRes.statusCode).toBe(200);
    expect(plateRes.json().data.length).toBe(2);

    // q as camera
    const camRes = await app.inject({
      method: 'GET',
      url: '/api/events?q=CAM-01',
    });
    expect(camRes.statusCode).toBe(200);
    expect(camRes.json().data.length).toBe(1);
    expect(camRes.json().data[0].camera_id).toBe('CAM-01');
  });

  it('GET /api/events enforces purpose requirement for person_id lookups (ADR 0024)', async () => {
    // Missing purpose -> 422 PURPOSE_REQUIRED
    const failRes = await app.inject({
      method: 'GET',
      url: '/api/events?person_id=PERSON-0042',
    });
    expect(failRes.statusCode).toBe(422);
    expect(failRes.json().error.code).toBe('PURPOSE_REQUIRED');

    // With purpose >= 5 chars -> 200
    const okRes = await app.inject({
      method: 'GET',
      url: '/api/events?person_id=PERSON-0042&purpose=Investigation%20Case%20Ref%20123',
    });
    expect(okRes.statusCode).toBe(200);
    expect(okRes.json().data.length).toBe(1);
    expect(okRes.json().data[0].person_id).toBe('PERSON-0042');
  });

  it('GET /api/events validates that time-of-day requires date bounds', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?time_from=02:00&time_to=03:00',
    });
    expect(res.statusCode).toBe(400);
    expect(res.json().error.message).toContain('Date range (from and to) is required');
  });

  it('GET /api/events/:id returns full detail with explanation', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events/11111111-1111-1111-1111-111111111111',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.event_id).toBe('11111111-1111-1111-1111-111111111111');
    expect(body.data.explanation).toEqual({ factors: [{ name: 'restricted_zone', points: 40 }] });
  });

  it('GET /api/events/:id returns 400 for non-UUID id', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events/not-a-uuid',
    });

    expect(res.statusCode).toBe(400);
  });
});
