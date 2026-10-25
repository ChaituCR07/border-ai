import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { AnalyticsService } from './service.js';
import type { AnalyticsRepo } from './repo.js';
import {
  AnalyticsTimeQuerySchema,
  AnalyticsEventsSchema,
  AnalyticsCamerasSchema,
  AnalyticsThreatsSchema,
} from './schemas.js';

export interface AnalyticsRouteDeps {
  analyticsRepo: AnalyticsRepo;
}

export function analyticsRoutes(deps: AnalyticsRouteDeps): FastifyPluginAsync {
  const service = new AnalyticsService(deps.analyticsRepo);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/analytics/events',
      {
        schema: {
          tags: ['Analytics'],
          summary: 'Time series analytics for events with zero-filling',
          querystring: AnalyticsTimeQuerySchema,
          response: {
            200: AnalyticsEventsSchema,
          },
        },
      },
      async (req) => {
        return service.getEvents(req.query);
      }
    );

    app.get(
      '/analytics/cameras',
      {
        schema: {
          tags: ['Analytics'],
          summary: 'Camera operational activity counters',
          querystring: z.object({
            from: z.string().datetime({ offset: true }).optional(),
            to: z.string().datetime({ offset: true }).optional(),
          }).strict(),
          response: {
            200: AnalyticsCamerasSchema,
          },
        },
      },
      async (req) => {
        return service.getCameras(req.query);
      }
    );

    app.get(
      '/analytics/threats',
      {
        schema: {
          tags: ['Analytics'],
          summary: 'Threat metrics, score histogram, and priority counters',
          querystring: z.object({
            camera_id: z.string().optional(),
            from: z.string().datetime({ offset: true }).optional(),
            to: z.string().datetime({ offset: true }).optional(),
          }).strict(),
          response: {
            200: AnalyticsThreatsSchema,
          },
        },
      },
      async (req) => {
        return service.getThreats(req.query);
      }
    );
  };
}
