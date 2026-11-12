import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryAnalyticsRepo } from '../../src/modules/analytics/repo.memory.js';

describe('Analytics Operator False-Positive Feedback', () => {
  let app: FastifyInstance;
  let repo: InMemoryAnalyticsRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.analyticsRepo;

    repo.seed(
      [],
      [
        {
          alert_id: 'a1',
          priority: 'HIGH',
          status: 'RESOLVED',
          resolution: 'FALSE_POSITIVE',
          resolution_note: 'Foliage shadow jitter',
          resolved_at: '2026-11-12T10:00:00.000000Z',
          event: { camera_id: 'CAM-01', event_type: 'RESTRICTED_ZONE_ENTRY' },
        },
        {
          alert_id: 'a2',
          priority: 'CRITICAL',
          status: 'RESOLVED',
          resolution: 'TRUE_POSITIVE',
          resolution_note: 'Verified intruder apprehension',
          resolved_at: '2026-11-12T10:30:00.000000Z',
          event: { camera_id: 'CAM-01', event_type: 'RESTRICTED_ZONE_ENTRY' },
        },
        {
          alert_id: 'a3',
          priority: 'HIGH',
          status: 'RESOLVED',
          resolution: 'FALSE_POSITIVE',
          resolution_note: 'ID switch reversed flow',
          resolved_at: '2026-11-12T11:00:00.000000Z',
          event: { camera_id: 'CAM-02', event_type: 'LINE_CROSSING_WRONG_DIRECTION' },
        },
      ],
      [{ camera_id: 'CAM-01' }, { camera_id: 'CAM-02' }]
    );
  });

  it('allows OPERATOR to retrieve false-positive resolution analytics', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/analytics/resolutions',
      headers: {
        'x-actor-role': 'OPERATOR',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.total_resolved).toBe(3);
    expect(body.data.false_positive_count).toBe(2);
    expect(body.data.false_positive_rate).toBeCloseTo(0.6667, 3);

    // Verify privacy: resolution_note is NOT in output
    const strBody = JSON.stringify(body);
    expect(strBody).not.toContain('Foliage shadow jitter');
    expect(strBody).not.toContain('Verified intruder apprehension');
  });

  it('rejects unauthorized VIEWER role with 403 Forbidden', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/analytics/resolutions',
      headers: {
        'x-actor-role': 'VIEWER',
      },
    });

    expect(res.statusCode).toBe(403);
  });

  it('exports CSV formatted analytics report', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/analytics/resolutions?format=csv',
      headers: {
        'x-actor-role': 'ADMIN',
      },
    });

    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toContain('text/csv');
    const text = res.body;
    expect(text).toContain('category,key,total,false_positives,false_positive_rate');
    expect(text).toContain('overall,TOTAL,3,2,0.6667');
    expect(text).toContain('camera,CAM-01,2,1');
    expect(text).toContain('camera,CAM-02,1,1');
  });
});
