import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { EventsService } from './service.js';
import type { EventsRepo } from './repo.js';
import type { InvestigationRepo } from '../investigation/repo.js';
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
        return service.list(req.query);
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
