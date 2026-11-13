import { FastifyInstance, FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import { signStreamToken } from '../../security/jwt.js';

export interface StreamRouteDeps {
  mjpegBaseUrl?: string;
}

const StreamTokenRequestSchema = z.object({
  camera_id: z.string().min(1).max(64),
});

export function streamRoutes(deps: StreamRouteDeps = {}): FastifyPluginAsync {
  const mjpegBase = deps.mjpegBaseUrl || process.env.MJPEG_BASE_URL || 'http://localhost:8001';

  return async (app: FastifyInstance) => {
    app.post(
      '/streams/token',
      {
        config: { permission: 'live:view' },
        schema: {
          tags: ['Cameras'],
          summary: 'Obtain an EdDSA signed stream token for live MJPEG viewing (60s connect window)',
          body: StreamTokenRequestSchema,
        },
      },
      async (req) => {
        const { camera_id } = req.body as { camera_id: string };
        const userId = req.actor?.id || 'anonymous';

        const token = signStreamToken({
          userId,
          cameraId: camera_id,
          ttlSeconds: 60,
        });

        const cleanBase = mjpegBase.replace(/\/+$/, '');
        const streamUrl = `${cleanBase}/cam/${camera_id}.mjpg?token=${token}`;

        return {
          url: streamUrl,
          token,
          expires_in: 60,
          max_duration_s: 900, // 15 minutes max stream session
        };
      }
    );
  };
}
