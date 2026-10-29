import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';

describe('Event Context route GET /api/events/:id/context', () => {
  let app: FastifyInstance;
  let repo: InMemoryEventsRepo;

  const targetEventId = '11111111-1111-1111-1111-111111111111';
  const sameCamNearbyId = '22222222-2222-2222-2222-222222222222';
  const sameCamFarId = '33333333-3333-3333-3333-333333333333';
  const otherCamLookalikeId = '44444444-4444-4444-4444-444444444444';
  const otherCamFarId = '55555555-5555-5555-5555-555555555555';

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.eventsRepo;

    // Seed test fixtures around 2026-10-25T10:00:00.000Z
    await repo.seed([
      {
        event_id: targetEventId,
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        track_id: '101',
        severity: 'HIGH',
        threat_score: 85,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: 'CAM-01/target.jpg',
        plate: 'KA01AB1234',
        metadata: { vehicle_id: 'VEH-999' },
      },
      // Same camera, +30 seconds (within default window_s=60)
      {
        event_id: sameCamNearbyId,
        camera_id: 'CAM-01',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        track_id: '102',
        severity: 'CRITICAL',
        threat_score: 95,
        timestamp: '2026-10-25T10:00:30.000000Z',
        snapshot_path: 'CAM-01/nearby.jpg',
        plate: 'MH02XY9999',
        metadata: {},
      },
      // Same camera, +120 seconds (outside default 60s, inside 180s)
      {
        event_id: sameCamFarId,
        camera_id: 'CAM-01',
        event_type: 'PERSON_DETECTED',
        track_id: '103',
        severity: 'LOW',
        threat_score: 20,
        timestamp: '2026-10-25T10:02:00.000000Z',
        snapshot_path: null,
        metadata: {},
      },
      // Different camera (CAM-02), +5 minutes (within 15 min), lookalike plate KA0IAB1234
      {
        event_id: otherCamLookalikeId,
        camera_id: 'CAM-02',
        event_type: 'VEHICLE_SPEEDING',
        track_id: '201',
        severity: 'HIGH',
        threat_score: 88,
        timestamp: '2026-10-25T10:05:00.000000Z',
        snapshot_path: 'CAM-02/speed.jpg',
        plate: 'KA0IAB1234', // 'I' is look-alike for '1'
        metadata: { vehicle_id: 'VEH-999' },
      },
      // Different camera (CAM-03), +30 minutes (outside 15 min window)
      {
        event_id: otherCamFarId,
        camera_id: 'CAM-03',
        event_type: 'VEHICLE_DETECTED',
        track_id: '301',
        severity: 'MEDIUM',
        threat_score: 50,
        timestamp: '2026-10-25T10:30:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        metadata: {},
      },
    ]);

    await repo.linkAlert(targetEventId, {
      alert_id: 'ALT-1001',
      status: 'OPEN',
      priority: 'HIGH',
    });
  });

  it('returns 404 for unknown event id', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events/99999999-9999-9999-9999-999999999999/context',
    });
    expect(res.statusCode).toBe(404);
  });

  it('returns context with default 60s window for same camera', async () => {
    const res = await app.inject({
      method: 'GET',
      url: `/api/events/${targetEventId}/context`,
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data).toBeDefined();
    expect(body.data.event.event_id).toBe(targetEventId);
    expect(body.data.alert).toEqual({
      alert_id: 'ALT-1001',
      status: 'OPEN',
      priority: 'HIGH',
    });

    // same_camera_around includes +30s event, excludes the target itself and excludes +120s event
    const sameCamIds = body.data.same_camera_around.map((e: any) => e.event_id);
    expect(sameCamIds).toContain(sameCamNearbyId);
    expect(sameCamIds).not.toContain(targetEventId);
    expect(sameCamIds).not.toContain(sameCamFarId);

    // same_subject_elsewhere includes CAM-02 lookalike plate within 15 min, excludes >15 min
    const elsewhereIds = body.data.same_subject_elsewhere.map((e: any) => e.event_id);
    expect(elsewhereIds).toContain(otherCamLookalikeId);
    expect(elsewhereIds).not.toContain(otherCamFarId);
  });

  it('widens same camera window when window_s parameter is provided', async () => {
    const res = await app.inject({
      method: 'GET',
      url: `/api/events/${targetEventId}/context?window_s=180`,
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    const sameCamIds = body.data.same_camera_around.map((e: any) => e.event_id);
    expect(sameCamIds).toContain(sameCamNearbyId);
    expect(sameCamIds).toContain(sameCamFarId);
  });
});
