import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryAlertsRepo } from '../../src/modules/alerts/repo.memory.js';
import type { InMemoryAuditRepo } from '../../src/common/audit.js';

describe('Alerts routes', () => {
  let app: FastifyInstance;
  let repo: InMemoryAlertsRepo;
  let audit: InMemoryAuditRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.alertsRepo;
    audit = res.auditRepo;

    await repo.seed([
      {
        alert_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        event_id: '11111111-1111-1111-1111-111111111111',
        priority: 'CRITICAL',
        status: 'OPEN',
        acknowledged_by: null,
        acknowledged_at: null,
        created_at: '2026-10-25T02:15:00.000000Z',
        event: {
          camera_id: 'CAM-01',
          event_type: 'RESTRICTED_ZONE_ENTRY',
          threat_score: 95,
          plate: 'KA01AB1234',
          snapshot_url: '/api/snapshots/CAM-01/snap1.jpg',
        },
      },
    ]);
  });

  it('GET /api/alerts returns alert list with embedded event summary', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/alerts',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.length).toBe(1);
    expect(body.data[0].event.camera_id).toBe('CAM-01');
    expect(body.data[0].event.threat_score).toBe(95);
  });

  it('PATCH /api/alerts/:id/acknowledge updates status to ACKNOWLEDGED idempotently', async () => {
    const res1 = await app.inject({
      method: 'PATCH',
      url: '/api/alerts/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/acknowledge',
      payload: { acknowledged_by: 'operator.42' },
    });

    expect(res1.statusCode).toBe(200);
    expect(res1.json().data.status).toBe('ACKNOWLEDGED');
    expect(res1.json().data.acknowledged_by).toBe('operator.42');

    const auditLogs1 = await audit.list();
    expect(auditLogs1.length).toBe(1);
    expect(auditLogs1[0]?.action).toBe('ALERT_ACK');

    // Second acknowledge (idempotent, preserves original acknowledger)
    const res2 = await app.inject({
      method: 'PATCH',
      url: '/api/alerts/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/acknowledge',
      payload: { acknowledged_by: 'operator.99' },
    });

    expect(res2.statusCode).toBe(200);
    expect(res2.json().data.status).toBe('ACKNOWLEDGED');
    expect(res2.json().data.acknowledged_by).toBe('operator.42'); // Preserved!

    // No duplicate audit log entry
    const auditLogs2 = await audit.list();
    expect(auditLogs2.length).toBe(1);
  });

  it('handles concurrent acknowledgement calls race-safely', async () => {
    const calls = Array.from({ length: 10 }, (_, i) =>
      app.inject({
        method: 'PATCH',
        url: '/api/alerts/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/acknowledge',
        payload: { acknowledged_by: `operator.${i}` },
      })
    );

    const responses = await Promise.all(calls);
    for (const res of responses) {
      expect(res.statusCode).toBe(200);
      expect(res.json().data.status).toBe('ACKNOWLEDGED');
    }

    const auditLogs = await audit.list();
    expect(auditLogs.length).toBe(1); // Exactly one audit record written!
  });
});
