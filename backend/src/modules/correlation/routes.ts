import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import type { CorrelationRepo } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { requireRole } from '../../common/auth.js';

export const TopologyResponseSchema = z.object({
  version: z.string(),
  cameras: z.array(
    z.object({
      camera_id: z.string(),
      name: z.string(),
      location_label: z.string(),
      map_x: z.number(),
      map_y: z.number(),
    })
  ),
  links: z.array(
    z.object({
      a: z.string(),
      b: z.string(),
      min_s: z.number(),
      typical_s: z.number(),
      max_s: z.number(),
      direction: z.enum(['both', 'a_to_b']).optional(),
      overlap: z.boolean().optional(),
    })
  ),
});

export interface CorrelationRouteDeps {
  correlationRepo: CorrelationRepo;
  auditRepo?: AuditRepo;
}

export function correlationRoutes(deps: CorrelationRouteDeps): FastifyPluginAsync {
  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/topology',
      {
        preHandler: requireRole('ADMIN', 'OPERATOR', 'INVESTIGATOR', 'VIEWER'),
        schema: {
          tags: ['Correlation'],
          summary: 'Get camera topology layout and link graph',
          response: {
            200: TopologyResponseSchema,
          },
        },
      },
      async () => {
        return deps.correlationRepo.getTopology();
      }
    );
  };
}
