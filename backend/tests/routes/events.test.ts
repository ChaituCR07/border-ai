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
        camera_id: 'CAM-01',
        event_type: 'LOITERING',
        track_id: '43',
        severity: 'MEDIUM',
        threat_score: 45,
        timestamp: '2026-10-25T02:10:00.000000Z',
        snapshot_path: null,
        plate: null,
        metadata: {},
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
    expect(body.data.length).toBe(2);
    expect(body.data[0].event_id).toBe('11111111-1111-1111-1111-111111111111');
    expect(body.meta.limit).toBe(10);
    expect(body.meta.has_more).toBe(false);
  });

  it('GET /api/events filters by severity and camera_id', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?severity=CRITICAL&camera_id=CAM-01',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(1);
    expect(body.data[0].severity).toBe('CRITICAL');
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
