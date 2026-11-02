import { describe, expect, it, vi, beforeEach } from 'vitest';
import Fastify from 'fastify';
import { serializerCompiler, validatorCompiler } from 'fastify-type-provider-zod';
import { notificationRoutes } from '../../src/modules/notifications/routes.js';
import { authenticate } from '../../src/common/auth.js';
import { errorHandler } from '../../src/common/errors.js';

describe('Admin Notification Endpoints', () => {
  let app: any;
  let mockRepo: any;
  let mockAudit: any;

  beforeEach(async () => {
    mockRepo = {
      list: vi.fn(async () => [
        {
          notification_id: '11111111-1111-1111-1111-111111111111',
          alert_id: 'alt-1',
          kind: 'ALERT',
          channel: 'email',
          route_name: 'critical-main',
          recipient: 'control-room@example.org',
          priority: 'CRITICAL',
          group_key: 'CAM-01|plate:KA01AB1234',
          status: 'SENT',
          skip_reason: null,
          attempts: 1,
          last_error: null,
          message_id: '<msg-1@border-ai.local>',
          sent_at: '2026-11-02T12:00:05.000Z',
          created_at: '2026-11-02T12:00:00.000Z',
        },
      ]),
      getQueueStats: vi.fn(async () => ({
        pending: 2,
        sending: 1,
        failed: 0,
        sent_24h: 15,
        skipped_24h: 3,
        oldest_pending_age_s: 45,
        stale_alerts_24h: 0,
      })),
      retry: vi.fn(async (id: string) => id === '22222222-2222-2222-2222-222222222222'),
      enqueueTest: vi.fn(async () => '33333333-3333-3333-3333-333333333333'),
    };

    mockAudit = {
      record: vi.fn(async () => {}),
    };

    app = Fastify();
    app.setValidatorCompiler(validatorCompiler);
    app.setSerializerCompiler(serializerCompiler);
    app.setErrorHandler(errorHandler);
    app.addHook('preHandler', authenticate);

    await app.register(
      notificationRoutes({
        repo: mockRepo,
        auditRepo: mockAudit,
        allowedDomains: ['example.org', 'border-ai.local'],
      }),
      { prefix: '/api' }
    );
  });

  describe('GET /api/notifications', () => {
    it('returns delivery log with masked recipients by default', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/notifications',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.data).toHaveLength(1);
      expect(body.data[0].recipient).toBe('c***m@example.org'); // Masked
      expect(mockAudit.record).not.toHaveBeenCalled();
    });

    it('returns unmasked recipients and audits when reveal=1', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/notifications?reveal=1',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.data[0].recipient).toBe('control-room@example.org'); // Unmasked
      expect(mockAudit.record).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'NOTIFICATION_RECIPIENT_REVEAL',
        })
      );
    });

    it('denies access to non-admin roles with 403 Forbidden', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/notifications',
        headers: {
          'x-actor-id': 'op-bob',
          'x-actor-role': 'OPERATOR',
        },
      });

      expect(res.statusCode).toBe(403);
    });
  });

  describe('GET /api/notifications/status', () => {
    it('returns queue statistics and planner status to Admin', async () => {
      const res = await app.inject({
        method: 'GET',
        url: '/api/notifications/status',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.data.queue.pending).toBe(2);
      expect(body.data.queue.sent_24h).toBe(15);
      expect(body.data.oldest_pending_age_s).toBe(45);
    });
  });

  describe('POST /api/notifications/test', () => {
    it('enqueues test email for allow-listed domain and audits', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/notifications/test',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
        payload: {
          recipient: 'test@example.org',
        },
      });

      expect(res.statusCode).toBe(200);
      const body = res.json();
      expect(body.data.notification_id).toBe('33333333-3333-3333-3333-333333333333');
      expect(mockAudit.record).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'NOTIFICATION_TEST_SEND',
        })
      );
    });

    it('rejects recipient outside allowed domains with 400 Bad Request', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/notifications/test',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
        payload: {
          recipient: 'user@gmail.com',
        },
      });

      expect(res.statusCode).toBe(400);
    });
  });

  describe('POST /api/notifications/retry/:id', () => {
    it('retries failed notification for eligible ID', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/notifications/retry/22222222-2222-2222-2222-222222222222',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
      });

      expect(res.statusCode).toBe(200);
      expect(res.json().data.retried).toBe(true);
      expect(mockAudit.record).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'NOTIFICATION_RETRY',
        })
      );
    });

    it('returns 404 for unknown or ineligible notification ID', async () => {
      const res = await app.inject({
        method: 'POST',
        url: '/api/notifications/retry/99999999-9999-9999-9999-999999999999',
        headers: {
          'x-actor-id': 'admin-alice',
          'x-actor-role': 'ADMIN',
        },
      });

      expect(res.statusCode).toBe(404);
    });
  });
});
