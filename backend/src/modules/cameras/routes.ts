import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { CamerasService } from './service.js';
import type { CamerasRepo } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { CreateCameraSchema, UpdateCameraSchema, CameraQuerySchema, CameraResourceSchema, CameraIdSchema } from './schemas.js';
import { requireRole } from '../../common/auth.js';

export interface CameraRouteDeps {
  camerasRepo: CamerasRepo;
  auditRepo?: AuditRepo;
}

export function cameraRoutes(deps: CameraRouteDeps): FastifyPluginAsync {
  const service = new CamerasService(deps.camerasRepo, deps.auditRepo);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/cameras',
      {
        schema: {
          tags: ['Cameras'],
          summary: 'List cameras with optional filters',
          querystring: CameraQuerySchema,
          response: {
            200: z.object({
              data: z.array(CameraResourceSchema),
            }),
          },
        },
      },
      async (req) => {
        const cameras = await service.list(req.query);
        return { data: cameras };
      }
    );

    app.post(
      '/cameras',
      {
        preHandler: requireRole('ADMIN'),
        schema: {
          tags: ['Cameras'],
          summary: 'Register a new camera',
          body: CreateCameraSchema,
          response: {
            201: z.object({
              data: CameraResourceSchema,
            }),
          },
        },
      },
      async (req, reply) => {
        const created = await service.create(req.body, req.actor, req.id);
        reply.header('Location', `/api/cameras/${created.camera_id}`);
        return reply.status(201).send({ data: created });
      }
    );

    app.get(
      '/cameras/:id',
      {
        schema: {
          tags: ['Cameras'],
          summary: 'Get camera details by ID',
          params: z.object({ id: CameraIdSchema }),
          response: {
            200: z.object({
              data: CameraResourceSchema,
            }),
          },
        },
      },
      async (req) => {
        const camera = await service.get(req.params.id);
        return { data: camera };
      }
    );

    app.put(
      '/cameras/:id',
      {
        preHandler: requireRole('ADMIN'),
        schema: {
          tags: ['Cameras'],
          summary: 'Update mutable camera properties',
          params: z.object({ id: CameraIdSchema }),
          body: UpdateCameraSchema,
          response: {
            200: z.object({
              data: CameraResourceSchema,
            }),
          },
        },
      },
      async (req) => {
        const updated = await service.update(req.params.id, req.body, req.actor, req.id);
        return { data: updated };
      }
    );
  };
}
