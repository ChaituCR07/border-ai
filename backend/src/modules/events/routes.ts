import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { EventsService } from './service.js';
import type { EventsRepo } from './repo.js';
import type { InvestigationRepo } from '../investigation/repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { AppError } from '../../common/errors.js';
import {
  EventQuerySchema,
  EventItemSchema,
  EventDetailSchema,
  EventIdSchema,
  EventContextQuerySchema,
  EventContextResponseSchema,
} from './schemas.js';

export interface EventRouteDeps {
  eventsRepo: EventsRepo;
  investigationRepo?: InvestigationRepo;
  snapshotDir: string;
  auditRepo?: AuditRepo;
}

export function eventRoutes(deps: EventRouteDeps): FastifyPluginAsync {
  const service = new EventsService(deps.eventsRepo, deps.snapshotDir, deps.investigationRepo);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/events',
      {
        schema: {
          tags: ['Events'],
          summary: 'List events with keyset pagination and filtering',
          querystring: EventQuerySchema,
          response: {
            200: z.object({
              data: z.array(EventItemSchema),
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
        const query = req.query as any;

        // Role & purpose gating for person search (ADR 0024)
        if (query.person_id) {
          const role = (req as any).actor?.role;
          if (role !== 'INVESTIGATOR' && role !== 'ADMIN') {
            throw new AppError(403, 'FORBIDDEN', 'Person searches are restricted to investigators');
          }
          if (!query.purpose || query.purpose.trim().length < 5) {
            throw new AppError(422, 'PURPOSE_REQUIRED', 'Person search requires a purpose (>= 5 chars)');
          }
        }

        const result = await service.list(query);

        // Audit logging for sensitive searches (plate, vehicle, person)
        if (query.plate || query.vehicle_id || query.person_id) {
          deps.auditRepo?.record({
            actor: (req as any).actor?.id ?? 'anonymous',
            action: 'SEARCH',
            entity_type: query.person_id ? 'person' : query.vehicle_id ? 'vehicle' : 'plate',
            entity_id: query.person_id ?? query.vehicle_id ?? query.plate ?? '',
            request_id: req.id,
            detail: {
              actor_role: (req as any).actor?.role,
              endpoint: '/api/events',
              query_json: query,
              purpose: query.purpose,
              row_count: result.data.length,
              ip: req.ip,
            },
          }).catch(() => {});
        }

        return result;
      }
    );

    app.get(
      '/events/:id/context',
      {
        schema: {
          tags: ['Events', 'Investigation'],
          summary: 'Get temporal camera and subject context around an event',
          params: z.object({ id: EventIdSchema }),
          querystring: EventContextQuerySchema,
          response: {
            200: EventContextResponseSchema,
          },
        },
      },
      async (req) => {
        return service.getContext(req.params.id, req.query.window_s, (req as any).actor?.role);
      }
    );

    app.get(
      '/events/:id',
      {
        schema: {
          tags: ['Events'],
          summary: 'Get event details by UUID',
          params: z.object({ id: EventIdSchema }),
          response: {
            200: z.object({
              data: EventDetailSchema,
            }),
          },
        },
      },
      async (req) => {
        const event = await service.get(req.params.id);
        return { data: event };
      }
    );
  };
}
