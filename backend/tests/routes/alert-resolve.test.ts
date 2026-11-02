import { describe, expect, it, vi, beforeEach } from 'vitest';
import Fastify from 'fastify';
import { serializerCompiler, validatorCompiler } from 'fastify-type-provider-zod';
import { alertRoutes } from '../../src/modules/alerts/routes.js';
import { InMemoryAlertsRepo } from '../../src/modules/alerts/repo.memory.js';
import { type AlertResource } from '../../src/types/domain.js';
import { authenticate } from '../../src/common/auth.js';

describe('PATCH /api/alerts/:id/resolve Route Tests', () => {
  let app: any;
  let repo: InMemoryAlertsRepo;
  let auditRepo: any;
  let onAlertChanged: any;

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
    auditRepo = { record: vi.fn(async () => {}) };
    onAlertChanged = vi.fn();

    app = Fastify();
    app.setValidatorCompiler(validatorCompiler);
    app.setSerializerCompiler(serializerCompiler);
    app.addHook('preHandler', authenticate);

    await app.register(
      alertRoutes({
        alertsRepo: repo,
        auditRepo,
        onAlertChanged,
      }),
      { prefix: '/api' }
    );
  });

  it('resolves an OPEN alert and records audit log', async () => {
    const res = await app.inject({
      method: 'PATCH',
      url: `/api/alerts/${validAlertId}/resolve`,
      headers: {
        'x-actor-id': 'op-alice',
        'x-actor-role': 'OPERATOR',
      },
      payload: {
        resolution: 'TRUE_POSITIVE',
        note: 'Confirmed security escort authorized',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.status).toBe('RESOLVED');
    expect(body.data.resolution).toBe('TRUE_POSITIVE');
    expect(body.data.resolved_by).toBe('op-alice');
    expect(body.data.acknowledged_by).toBe('op-alice'); // Implicit acknowledge

    // Verify audit log
    expect(auditRepo.record).toHaveBeenCalledTimes(1);
    expect(auditRepo.record).toHaveBeenCalledWith(
      expect.objectContaining({
        action: 'ALERT_RESOLVE',
        entity_id: validAlertId,
        actor: 'op-alice',
        detail: expect.objectContaining({
          resolution: 'TRUE_POSITIVE',
          note: 'Confirmed security escort authorized',
        }),
      })
    );

    // Verify broadcast
    expect(onAlertChanged).toHaveBeenCalledTimes(1);
  });

  it('rejects note longer than 500 characters with 400 Bad Request', async () => {
    const longNote = 'A'.repeat(501);
    const res = await app.inject({
      method: 'PATCH',
      url: `/api/alerts/${validAlertId}/resolve`,
      headers: {
        'x-actor-id': 'op-alice',
        'x-actor-role': 'OPERATOR',
      },
      payload: {
        resolution: 'FALSE_POSITIVE',
        note: longNote,
      },
    });

    expect(res.statusCode).toBe(400);
  });

  it('rejects invalid resolution enum with 400 Bad Request', async () => {
    const res = await app.inject({
      method: 'PATCH',
      url: `/api/alerts/${validAlertId}/resolve`,
      headers: {
        'x-actor-id': 'op-alice',
        'x-actor-role': 'OPERATOR',
      },
      payload: {
        resolution: 'INVALID_RESOLUTION_TYPE',
      },
    });

    expect(res.statusCode).toBe(400);
  });

  it('enforces role gating: VIEWER returns 403 Forbidden', async () => {
    const res = await app.inject({
      method: 'PATCH',
      url: `/api/alerts/${validAlertId}/resolve`,
      headers: {
        'x-actor-id': 'viewer-bob',
        'x-actor-role': 'VIEWER',
      },
      payload: {
        resolution: 'TRUE_POSITIVE',
      },
    });

    expect(res.statusCode).toBe(403);
  });
});
