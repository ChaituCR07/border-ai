import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryAnalyticsRepo } from '../../src/modules/analytics/repo.memory.js';

describe('Analytics routes', () => {
  let app: FastifyInstance;
  let repo: InMemoryAnalyticsRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.analyticsRepo;

    repo.seed(
      [
        {
          event_id: 'e1',
          camera_id: 'CAM-01',
          event_type: 'LINE_CROSSING',
          severity: 'CRITICAL',
          threat_score: 88,
          timestamp: '2026-10-25T02:00:00.000000Z',
        },
        {
          event_id: 'e2',
          camera_id: 'CAM-01',
          event_type: 'LOITERING',
          severity: 'MEDIUM',
          threat_score: 50,
          timestamp: '2026-10-25T02:30:00.000000Z',
        },
      ],
      [
        {
          alert_id: 'a1',
          priority: 'CRITICAL',
          status: 'OPEN',
          event: { camera_id: 'CAM-01' },
        },
      ],
      [
        { camera_id: 'CAM-01' },
        { camera_id: 'CAM-02' },
      ]
    );
  });

  it('GET /api/analytics/events returns zero-filled buckets with UTC timezone', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/analytics/events?from=2026-10-25T00:00:00Z&to=2026-10-25T04:00:00Z&bucket=hour',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.bucket_tz).toBe('UTC');
    expect(body.buckets.length).toBe(4); // 00, 01, 02, 03
    expect(body.buckets[2].total).toBe(2);
    expect(body.buckets[2].critical).toBe(1);
    expect(body.buckets[0].total).toBe(0); // Zero-filled!
  });

  it('GET /api/analytics/cameras returns operational stats for all cameras including 0 events', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/analytics/cameras',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(2);
    const cam1 = body.data.find((c: any) => c.camera_id === 'CAM-01');
    const cam2 = body.data.find((c: any) => c.camera_id === 'CAM-02');
    expect(cam1.events).toBe(2);
    expect(cam1.alerts_open).toBe(1);
    expect(cam2.events).toBe(0);
  });

  it('GET /api/analytics/threats returns score histograms and severity counts', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/analytics/threats?from=2026-10-25T00:00:00Z&to=2026-10-25T04:00:00Z',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.severity_counts.CRITICAL).toBe(1);
    expect(body.data.severity_counts.MEDIUM).toBe(1);
    expect(body.data.open_alerts_by_priority.CRITICAL).toBe(1);
    expect(body.data.score_histogram.length).toBe(10);
  });
});
