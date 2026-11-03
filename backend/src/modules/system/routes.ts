import type { FastifyPluginAsync } from 'fastify';
import { getSystemStatus, type SystemStatusDeps } from './systemStatus.js';

export function systemRoutes(deps: SystemStatusDeps): FastifyPluginAsync {
  return async (app) => {
    app.get('/system/status', async (_request, reply) => {
      const data = await getSystemStatus(deps);
      return reply.send({ data });
    });
  };
}
