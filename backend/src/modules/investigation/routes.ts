import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { InvestigationService } from './service.js';
import type { InvestigationRepo } from './repo.js';
import {
  FacetsQuerySchema,
  FacetsResponseSchema,
  SuggestQuerySchema,
  SuggestResponseSchema,
  JourneyQuerySchema,
  JourneyResponseSchema,
} from './schemas.js';

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

    app.get(
      '/investigation/suggest',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Typeahead suggestion for plates, cameras, and person identifiers',
          querystring: SuggestQuerySchema,
          response: {
            200: SuggestResponseSchema,
          },
        },
      },
      async (req) => {
        return service.suggest(req.query.kind, req.query.prefix, req.actor?.role);
      }
    );

    app.get(
      '/investigation/journey',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Get vehicle journey (chronological sightings and transitions)',
          querystring: JourneyQuerySchema,
          response: {
            200: JourneyResponseSchema,
          },
        },
      },
      async (req) => {
        return service.getJourney(req.query);
      }
    );
  };
}
