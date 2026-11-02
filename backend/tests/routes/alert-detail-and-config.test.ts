import { describe, expect, it, beforeEach } from 'vitest';
import Fastify from 'fastify';
import { serializerCompiler, validatorCompiler } from 'fastify-type-provider-zod';
import { alertRoutes } from '../../src/modules/alerts/routes.js';
import { configRoutes } from '../../src/modules/config/routes.js';
import { InMemoryAlertsRepo } from '../../src/modules/alerts/repo.memory.js';
import { authenticate } from '../../src/common/auth.js';
import { type AlertResource } from '../../src/types/domain.js';

describe('Alert Detail & Public Config Routes', () => {
  let app: any;
  let repo: InMemoryAlertsRepo;
  const validAlertId = '11111111-2222-3333-4444-555555555555';

  beforeEach(async () => {
    const initialAlerts: AlertResource[] = [
      {
        alert_id: validAlertId,
        event_id: '22222222-3333-4444-5555-666666666666',
        priority: 'CRITICAL',
        status: 'OPEN',
        acknowledged_by: null,
        acknowledged_at: null,
        created_at: '2026-11-02T12:00:00Z',
        event: {
          camera_id: 'CAM-01',
          event_type: 'RESTRICTED_ZONE_ENTRY',
          threat_score: 90,
          plate: 'KA01AB1234',
          snapshot_url: null,
        },
      },
    ];

    repo = new InMemoryAlertsRepo();
    await repo.seed(initialAlerts);

    app = Fastify();
    app.setValidatorCompiler(validatorCompiler);
    app.setSerializerCompiler(serializerCompiler);
    app.addHook('preHandler', authenticate);

    await app.register(alertRoutes({ alertsRepo: repo }), { prefix: '/api' });
    await app.register(configRoutes(), { prefix: '/api' });
  });

  describe('GET /api/config/public', () => {
    it('returns thresholds, escalation timing, and realtime config without auth requirements', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/config/public',
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.data.thresholds).toBeDefined();
      expect(body.data.thresholds.length).toBeGreaterThanOrEqual(4);
      expect(body.data.escalation.critical_after_s).toBeGreaterThanOrEqual(30);
      expect(body.data.realtime.heartbeat_ms).toBe(15000);
    });
  });

  describe('GET /api/alerts/:id', () => {
    it('returns single alert detail with notifications counts', async () => {
      const res = await app.inject({
        method: 'GET',
        url: `/api/alerts/${validAlertId}`,
        headers: {
          'x-actor-id': 'op-alice',
          'x-actor-role': 'OPERATOR',
        },
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.data.alert_id).toBe(validAlertId);
      expect(body.data.priority).toBe('CRITICAL');
      expect(body.data.notifications).toBeDefined();
      expect(body.data.notifications.sent).toBe(0);
      expect(body.data.notifications.pending).toBe(0);
    });

    it('returns 404 for unknown alert id', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/alerts/99999999-9999-9999-9999-999999999999',
        headers: {
          'x-actor-id': 'op-alice',
          'x-actor-role': 'OPERATOR',
        },
      });

      expect(res.statusCode).toBe(404);
    });

    it('returns 400 for invalid UUID alert id', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/alerts/not-a-uuid',
        headers: {
          'x-actor-id': 'op-alice',
          'x-actor-role': 'OPERATOR',
        },
      });

      expect(res.statusCode).toBe(400);
    });
  });
});
