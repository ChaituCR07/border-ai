import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { AnalyticsService } from './service.js';
import type { AnalyticsRepo } from './repo.js';
import { requireRole } from '../../common/auth.js';
import {
  AnalyticsTimeQuerySchema,
  AnalyticsEventsSchema,
  AnalyticsCamerasSchema,
  AnalyticsThreatsSchema,
  AnalyticsResolutionsQuerySchema,
  AnalyticsResolutionsSchema,
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

    app.get(
      '/analytics/resolutions',
      {
        preHandler: requireRole('ADMIN', 'OPERATOR', 'INVESTIGATOR'),
        schema: {
          tags: ['Analytics'],
          summary: 'Operator false positive feedback and alert resolution breakdown',
          querystring: AnalyticsResolutionsQuerySchema,
        },
      },
      async (req, reply) => {
        const query = req.query as { from?: string; to?: string; format?: 'json' | 'csv' };
        const result = await service.getResolutions(query);

        if (query.format === 'csv') {
          const lines: string[] = ['category,key,total,false_positives,false_positive_rate'];
          const overall = result.data;
          lines.push(`overall,TOTAL,${overall.total_resolved},${overall.false_positive_count},${overall.false_positive_rate}`);
          for (const c of overall.by_camera) {
            const r = c.total > 0 ? (c.false_positives / c.total).toFixed(4) : '0';
            lines.push(`camera,${c.camera_id},${c.total},${c.false_positives},${r}`);
          }
          for (const ru of overall.by_rule) {
            const r = ru.total > 0 ? (ru.false_positives / ru.total).toFixed(4) : '0';
            lines.push(`rule,${ru.rule_type},${ru.total},${ru.false_positives},${r}`);
          }
          for (const t of overall.by_tier) {
            const r = t.total > 0 ? (t.false_positives / t.total).toFixed(4) : '0';
            lines.push(`tier,${t.tier},${t.total},${t.false_positives},${r}`);
          }
          reply.header('Content-Type', 'text/csv; charset=utf-8');
          reply.header('Content-Disposition', 'attachment; filename="resolutions_analytics.csv"');
          return reply.send(lines.join('\n') + '\n');
        }

        return result;
      }
    );
  };
}
