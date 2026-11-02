import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { requireRole } from '../../common/auth.js';
import { clampLimit, decodeCursor, encodeCursor } from '../../common/pagination.js';
import { notFound, badRequest } from '../../common/errors.js';
import type { AuditRepo } from '../../common/audit.js';
import {
  NotificationsRepo,
  maskRecipient,
} from './repo.js';
import { domainAllowed } from './policy.js';
import { type NotificationPlanner } from './planner.js';
import { type NotificationWorker } from './worker.js';

export interface NotificationRouteDeps {
  repo: NotificationsRepo;
  planner?: NotificationPlanner;
  worker?: NotificationWorker;
  auditRepo?: AuditRepo;
  allowedDomains?: string[];
  enabled?: boolean;
  dryRun?: boolean;
}

export function notificationRoutes(deps: NotificationRouteDeps): FastifyPluginAsync {
  const allowed = deps.allowedDomains || ['example.org', 'border-ai.local'];
  const testRateLimiter: { [key: string]: number[] } = {};

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    // 1. GET /notifications - Delivery log (Admin only)
    app.get(
      '/notifications',
      {
        preHandler: requireRole('ADMIN'),
        schema: {
          tags: ['Notifications'],
          summary: 'Get notifications delivery log with keyset pagination (Admin only)',
          querystring: z.object({
            alert_id: z.string().optional(),
            status: z.string().optional(),
            kind: z.string().optional(),
            limit: z.coerce.number().int().min(1).max(200).default(50),
            cursor: z.string().optional(),
            reveal: z.preprocess(v => v === 'true' || v === '1', z.boolean().default(false)),
          }),
          response: {
            200: z.object({
              data: z.array(
                z.object({
                  notification_id: z.string().uuid(),
                  alert_id: z.string(),
                  kind: z.string(),
                  channel: z.string(),
                  route_name: z.string(),
                  recipient: z.string(),
                  priority: z.string(),
                  status: z.string(),
                  skip_reason: z.string().nullable(),
                  attempts: z.number(),
                  last_error: z.string().nullable(),
                  message_id: z.string().nullable(),
                  sent_at: z.string().nullable(),
                  created_at: z.string(),
                })
              ),
              meta: z.object({
                limit: z.number(),
                next_cursor: z.string().nullable(),
                has_more: z.boolean(),
              }),
            }),
          },
        },
      },
      async (req) => {
        const limit = clampLimit(req.query.limit, 50, 200);
        const cursor = req.query.cursor ? decodeCursor(req.query.cursor) : undefined;

        const rows = await deps.repo.list(
          {
            alertId: req.query.alert_id,
            status: req.query.status,
            kind: req.query.kind,
          },
          limit + 1,
          cursor
        );

        const hasMore = rows.length > limit;
        const pageRows = hasMore ? rows.slice(0, limit) : rows;

        // If reveal requested, audit and show raw recipient; else mask
        if (req.query.reveal && deps.auditRepo) {
          await deps.auditRepo.record({
            actor: req.actor.id,
            action: 'NOTIFICATION_RECIPIENT_REVEAL',
            entity_type: 'NOTIFICATIONS',
            entity_id: 'batch',
            request_id: req.id,
            detail: { count: pageRows.length },
          });
        }

        const data = pageRows.map(r => ({
          ...r,
          recipient: req.query.reveal ? r.recipient : maskRecipient(r.recipient),
        }));

        const nextCursor =
          hasMore && pageRows.length > 0
            ? encodeCursor({
                t: pageRows[pageRows.length - 1]!.created_at,
                id: pageRows[pageRows.length - 1]!.notification_id,
              })
            : null;

        return {
          data,
          meta: {
            limit,
            next_cursor: nextCursor,
            has_more: hasMore,
          },
        };
      }
    );

    // 2. GET /notifications/status - System status & queue stats (Admin only)
    app.get(
      '/notifications/status',
      {
        preHandler: requireRole('ADMIN'),
        schema: {
          tags: ['Notifications'],
          summary: 'Get notification system queue, planner, and SMTP status (Admin only)',
          response: {
            200: z.object({
              data: z.object({
                enabled: z.boolean(),
                dry_run: z.boolean(),
                smtp: z.object({
                  ok: z.boolean(),
                  last_error_class: z.string().nullable(),
                }),
                queue: z.object({
                  pending: z.number(),
                  sending: z.number(),
                  failed: z.number(),
                  sent_24h: z.number(),
                  skipped_24h: z.number(),
                }),
                oldest_pending_age_s: z.number().nullable(),
                planner: z.object({
                  active: z.boolean(),
                  is_standby: z.boolean(),
                }),
                stale_alerts_24h: z.number(),
              }),
            }),
          },
        },
      },
      async () => {
        const stats = await deps.repo.getQueueStats();
        const plannerStatus = deps.planner?.getStatus() || {
          active: true,
          isStandby: false,
        };

        return {
          data: {
            enabled: deps.enabled ?? true,
            dry_run: deps.dryRun ?? false,
            smtp: {
              ok: true,
              last_error_class: null,
            },
            queue: {
              pending: stats.pending,
              sending: stats.sending,
              failed: stats.failed,
              sent_24h: stats.sent_24h,
              skipped_24h: stats.skipped_24h,
            },
            oldest_pending_age_s: stats.oldest_pending_age_s,
            planner: {
              active: plannerStatus.active,
              is_standby: plannerStatus.isStandby,
            },
            stale_alerts_24h: stats.stale_alerts_24h,
          },
        };
      }
    );

    // 3. POST /notifications/test - Trigger test email (Admin only)
    app.post(
      '/notifications/test',
      {
        preHandler: requireRole('ADMIN'),
        schema: {
          tags: ['Notifications'],
          summary: 'Send a test email notification to an allow-listed recipient (Admin only)',
          body: z.object({
            recipient: z.string().email(),
          }),
          response: {
            200: z.object({
              data: z.object({
                notification_id: z.string().uuid(),
                recipient: z.string(),
                status: z.string(),
              }),
            }),
          },
        },
      },
      async (req) => {
        const rcpt = req.body.recipient.trim();
        if (!domainAllowed(rcpt, allowed)) {
          throw badRequest(`Recipient domain not in allowed domains list (${allowed.join(', ')})`);
        }

        // Rate limit: max 3 per min per admin
        const now = Date.now();
        const actorId = req.actor.id;
        const history = (testRateLimiter[actorId] || []).filter(t => t > now - 60000);
        if (history.length >= 3) {
          throw badRequest('Rate limit exceeded: maximum 3 test emails per minute.');
        }
        history.push(now);
        testRateLimiter[actorId] = history;

        const notifId = await deps.repo.enqueueTest(rcpt);

        if (deps.auditRepo) {
          await deps.auditRepo.record({
            actor: actorId,
            action: 'NOTIFICATION_TEST_SEND',
            entity_type: 'NOTIFICATION',
            entity_id: notifId,
            request_id: req.id,
            detail: { recipient: rcpt },
          });
        }

        return {
          data: {
            notification_id: notifId,
            recipient: rcpt,
            status: 'PENDING',
          },
        };
      }
    );

    // 4. POST /notifications/retry/:id - Retry a failed notification (Admin only)
    app.post(
      '/notifications/retry/:id',
      {
        preHandler: requireRole('ADMIN'),
        schema: {
          tags: ['Notifications'],
          summary: 'Retry a failed notification (Admin only)',
          params: z.object({
            id: z.string().uuid(),
          }),
          response: {
            200: z.object({
              data: z.object({
                retried: z.boolean(),
                notification_id: z.string().uuid(),
              }),
            }),
          },
        },
      },
      async (req) => {
        const success = await deps.repo.retry(req.params.id);
        if (!success) {
          throw notFound(`Failed notification '${req.params.id}' not found or not eligible for retry`);
        }

        if (deps.auditRepo) {
          await deps.auditRepo.record({
            actor: req.actor.id,
            action: 'NOTIFICATION_RETRY',
            entity_type: 'NOTIFICATION',
            entity_id: req.params.id,
            request_id: req.id,
          });
        }

        return {
          data: {
            retried: true,
            notification_id: req.params.id,
          },
        };
      }
    );
  };
}
