import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { InvestigationService } from './service.js';
import type { InvestigationRepo } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
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
  auditRepo?: AuditRepo;
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
        const result = await service.getJourney(req.query);

        deps.auditRepo?.record({
          actor: req.actor?.id ?? 'anonymous',
          action: 'JOURNEY',
          entity_type: req.query.vehicle_id ? 'vehicle' : 'plate',
          entity_id: req.query.vehicle_id ?? req.query.plate ?? '',
          request_id: req.id,
          detail: {
            actor_role: req.actor?.role,
            endpoint: '/api/investigation/journey',
            query_json: req.query,
            row_count: result.data.total_events,
            ip: req.ip,
          },
        }).catch(() => {});

        return result;
      }
    );
  };
}
