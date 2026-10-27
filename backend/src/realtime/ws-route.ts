import type { FastifyPluginAsync, FastifyRequest } from 'fastify';
import { ClientMessage, WS_CLOSE } from '@border-ai/protocol';
import { AppError } from '../common/errors.js';
import { authenticateWs } from '../common/auth.js';
import type { Hub } from './hub.js';
import type { AlertStreamConsumer } from './alert-stream-consumer.js';
import type { Config } from '../config/env.js';

export interface WsRouteDeps {
  hub: Hub;
  config: Config;
  consumer?: AlertStreamConsumer;
}

export const wsRoutes = (deps: WsRouteDeps): FastifyPluginAsync => async (app) => {
  // Realtime Status Inspection Endpoint
  app.get('/realtime/status', async (_req, reply) => {
    return reply.send({
      data: {
        clients: deps.hub.size,
        epoch: deps.hub.epoch,
        seq: deps.hub.currentSeq,
        consumer: {
          state: deps.consumer?.state ?? 'idle',
          last_entry_at: deps.consumer?.lastEntryAt
            ? new Date(deps.consumer.lastEntryAt).toISOString()
            : null,
          last_id: deps.consumer?.getLastId() ?? null,
        },
        malformed_total: deps.consumer?.malformedCount ?? 0,
      },
    });
  });

  // WebSocket Gateway Endpoint
  app.get(
    '/ws',
    {
      websocket: true,
      preValidation: async (req: FastifyRequest) => {
        const origin = req.headers.origin;
        if (origin) {
          const allowed = deps.config.corsOrigins;
          const isAllowed = allowed.includes('*') || allowed.includes(origin);
          if (!isAllowed) {
            throw new AppError(403, 'FORBIDDEN', `Origin ${origin} is not authorized for WebSocket connection`);
          }
        }
        req.actor = await authenticateWs(req);
      },
    },
    (socket, req) => {
      const clientId = deps.hub.add(socket, req.actor);
      if (!clientId) return;

      let msgTimestamps: number[] = [];

      socket.on('message', (raw: Buffer | string) => {
        const now = Date.now();
        msgTimestamps = [...msgTimestamps.filter((t) => now - t < 10_000), now];

        // Rate limit: > 20 messages in 10 seconds -> close with 1008 Policy Violation
        if (msgTimestamps.length > 20) {
          try {
            socket.close(WS_CLOSE.POLICY, 'rate limit exceeded');
          } catch {
            // Ignore
          }
          return;
        }

        const byteLength = Buffer.isBuffer(raw) ? raw.length : Buffer.byteLength(raw);
        if (byteLength > 1024) {
          try {
            socket.close(WS_CLOSE.TOO_BIG, 'message payload exceeds 1KB limit');
          } catch {
            // Ignore
          }
          return;
        }

        try {
          const text = raw.toString();
          const json = JSON.parse(text);
          const parsed = ClientMessage.safeParse(json);
          if (!parsed.success) {
            return; // Ignore malformed or unrecognised client messages gracefully
          }

          if (parsed.data.type === 'ping') {
            socket.send(
              JSON.stringify({
                v: 1,
                type: 'heartbeat',
                seq: deps.hub.currentSeq,
                server_time: new Date().toISOString(),
              })
            );
          }
        } catch {
          // Ignore invalid JSON
        }
      });
    }
  );
};
