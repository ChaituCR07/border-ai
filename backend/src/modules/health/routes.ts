import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type pg from 'pg';

export interface HealthRouteDeps {
  pool?: pg.Pool;
}

export function healthRoutes(deps: HealthRouteDeps): FastifyPluginAsync {
  return async (fastify: FastifyInstance) => {
    fastify.get('/health', async (_req, reply) => {
      return reply.status(200).send({
        status: 'ok',
        uptime: process.uptime(),
        timestamp: new Date().toISOString(),
      });
    });

    fastify.get('/ready', async (_req, reply) => {
      if (!deps.pool) {
        return reply.status(200).send({
          status: 'ready',
          database: 'memory_mode',
        });
      }

      try {
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('DB readiness probe timeout')), 2000)
        );
        await Promise.race([deps.pool.query('SELECT 1'), timeoutPromise]);

        return reply.status(200).send({
          status: 'ready',
          database: 'connected',
        });
      } catch (err) {
        fastify.log.warn({ err }, 'Readiness probe failed');
        return reply.status(503).send({
          status: 'unhealthy',
          database: 'disconnected',
        });
      }
    });
  };
}
