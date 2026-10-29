import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { InvestigationService } from './service.js';
import type { InvestigationRepo } from './repo.js';
import { FacetsQuerySchema, FacetsResponseSchema } from './schemas.js';

export interface InvestigationRouteDeps {
  investigationRepo: InvestigationRepo;
}

export function investigationRoutes(deps: InvestigationRouteDeps): FastifyPluginAsync {
  const service = new InvestigationService(deps.investigationRepo);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/investigation/facets',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Get disjunctive facet counts for investigation filters',
          querystring: FacetsQuerySchema,
          response: {
            200: FacetsResponseSchema,
          },
        },
      },
      async (req) => {
        return service.getFacets(req.query);
      }
    );
  };
}
