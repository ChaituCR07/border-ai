import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { AlertsService, type AlertChangeCallback } from './service.js';
import type { AlertsRepo } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { AlertQuerySchema, AlertResourceSchema, AlertIdSchema, AcknowledgeBodySchema } from './schemas.js';
import { requireRole } from '../../common/auth.js';

export interface AlertRouteDeps {
  alertsRepo: AlertsRepo;
  auditRepo?: AuditRepo;
  onAlertChanged?: AlertChangeCallback;
}

export function alertRoutes(deps: AlertRouteDeps): FastifyPluginAsync {
  const service = new AlertsService(deps.alertsRepo, deps.auditRepo, deps.onAlertChanged);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/alerts',
      {
        schema: {
          tags: ['Alerts'],
          summary: 'List alerts with filtering and pagination',
          querystring: AlertQuerySchema,
          response: {
            200: z.object({
              data: z.array(AlertResourceSchema),
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
        return service.list(req.query);
      }
    );

    app.patch(
      '/alerts/:id/acknowledge',
      {
        preHandler: requireRole('ADMIN', 'OPERATOR', 'INVESTIGATOR'),
        schema: {
          tags: ['Alerts'],
          summary: 'Acknowledge an alert (idempotent and race-safe)',
          params: z.object({ id: AlertIdSchema }),
          body: AcknowledgeBodySchema,
          response: {
            200: z.object({
              data: AlertResourceSchema,
            }),
          },
        },
      },
      async (req) => {
        const alert = await service.acknowledge(req.params.id, req.body?.acknowledged_by, req.actor, req.id);
        return { data: alert };
      }
    );
  };
}
