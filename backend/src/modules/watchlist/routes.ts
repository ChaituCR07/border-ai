import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { WatchlistService } from './service.js';
import type { WatchlistRepo } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
import {
  CreateWatchlistSchema,
  WatchlistQuerySchema,
  WatchlistResourceSchema,
  WatchlistIdSchema,
} from './schemas.js';
import { requireRole } from '../../common/auth.js';

export interface WatchlistRouteDeps {
  watchlistRepo: WatchlistRepo;
  auditRepo?: AuditRepo;
}

export function watchlistRoutes(deps: WatchlistRouteDeps): FastifyPluginAsync {
  const service = new WatchlistService(deps.watchlistRepo, deps.auditRepo);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/watchlist',
      {
        schema: {
          tags: ['Watchlist'],
          summary: 'List active watchlist entries',
          querystring: WatchlistQuerySchema,
          response: {
            200: z.object({
              data: z.array(WatchlistResourceSchema),
            }),
          },
        },
      },
      async (req) => {
        const items = await service.list(req.query);
        return { data: items };
      }
    );

    app.post(
      '/watchlist',
      {
        preHandler: requireRole('ADMIN', 'INVESTIGATOR'),
        schema: {
          tags: ['Watchlist'],
          summary: 'Create a new watchlist entry (strictly non-biometric)',
          body: CreateWatchlistSchema,
          response: {
            201: z.object({
              data: WatchlistResourceSchema,
            }),
          },
        },
      },
      async (req, reply) => {
        const created = await service.create(req.body, req.actor, req.id);
        reply.header('Location', `/api/watchlist/${created.entity_id}`);
        return reply.status(201).send({ data: created });
      }
    );

    app.delete(
      '/watchlist/:id',
      {
        preHandler: requireRole('ADMIN', 'INVESTIGATOR'),
        schema: {
          tags: ['Watchlist'],
          summary: 'Soft-delete a watchlist entry (idempotent)',
          params: z.object({ id: WatchlistIdSchema }),
          response: {
            204: z.undefined(),
          },
        },
      },
      async (req, reply) => {
        await service.delete(req.params.id, req.actor, req.id);
        return reply.status(204).send();
      }
    );
  };
}
