import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import type { CorrelationRepo } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { AppError } from '../../common/errors.js';
import {
  SequenceQuerySchema,
  parseCameraSequence,
} from './sequence.js';

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

export const SequenceResponseSchema = z.object({
  data: z.array(
    z.object({
      plate_key: z.string(),
      representative_plate: z.string(),
      plate_variants: z.array(z.string()),
      hops: z.array(
        z.object({
          camera_id: z.string(),
          timestamp: z.string(),
          event_id: z.string(),
        })
      ),
      total_duration_s: z.number(),
    })
  ),
  meta: z.object({
    steps: z.number(),
    cameras: z.array(z.string()),
    total: z.number(),
    limit: z.number(),
  }),
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
        config: { permission: 'cameras:view' },
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

    app.get(
      '/correlation/sequence',
      {
        config: { permission: 'investigation:sequence' },
        schema: {
          tags: ['Correlation'],
          summary: 'Search for multi-camera vehicle sequences',
          querystring: SequenceQuerySchema,
          response: {
            200: SequenceResponseSchema,
          },
        },
      },
      async (req) => {
        const spanMs = new Date(req.query.to).getTime() - new Date(req.query.from).getTime();
        const maxSpanMs = 7 * 24 * 3600 * 1000;
        if (spanMs > maxSpanMs) {
          throw new AppError(400, 'VALIDATION_ERROR', 'Maximum sequence time span is 7 days');
        }

        const cameras = parseCameraSequence(req.query.cams);

        const matches = await deps.correlationRepo.sequenceSearch({
          cameras,
          from: req.query.from,
          to: req.query.to,
          maxHopGapS: req.query.max_hop_gap_s,
          limit: req.query.limit,
        });

        deps.auditRepo?.record({
          actor: req.actor?.id ?? 'anonymous',
          action: 'SEQUENCE_SEARCH',
          entity_type: 'sequence',
          entity_id: cameras.join('->'),
          request_id: req.id,
          detail: {
            actor_role: req.actor?.role,
            cams: cameras,
            from: req.query.from,
            to: req.query.to,
            max_hop_gap_s: req.query.max_hop_gap_s,
            purpose: req.query.purpose,
            row_count: matches.length,
            limit: req.query.limit,
          },
        }).catch(() => {});

        return {
          data: matches,
          meta: {
            steps: cameras.length,
            cameras,
            total: matches.length,
            limit: req.query.limit,
          },
        };
      }
    );
  };
}
