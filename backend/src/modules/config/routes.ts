import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import {
  loadThreatThresholdConfig,
  type ThreatThresholdConfig,
} from '../../config/thresholds.js';
import {
  loadNotificationConfig,
  type NotificationConfig,
} from '../notifications/config.js';

export interface PublicConfigDeps {
  thresholdsConfig?: ThreatThresholdConfig;
  notificationsConfig?: NotificationConfig;
}

export function configRoutes(deps: PublicConfigDeps = {}): FastifyPluginAsync {
  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/config/public',
      {
        schema: {
          tags: ['Config'],
          summary: 'Get public system configuration for dashboard and escalation timing',
          response: {
            200: z.object({
              data: z.object({
                thresholds: z.array(
                  z.object({
                    name: z.string(),
                    min: z.number(),
                  })
                ),
                escalation: z.object({
                  critical_after_s: z.number(),
                }),
                realtime: z.object({
                  heartbeat_ms: z.number(),
                }),
              }),
            }),
          },
        },
      },
      async () => {
        let tc: ThreatThresholdConfig;
        try {
          tc = deps.thresholdsConfig || loadThreatThresholdConfig();
        } catch {
          tc = {
            version: 1,
            tiers: [
              { name: 'LOW', min: 0 },
              { name: 'MEDIUM', min: 30 },
              { name: 'HIGH', min: 60 },
              { name: 'CRITICAL', min: 80 },
            ],
          };
        }

        let nc: NotificationConfig | null = null;
        try {
          nc = deps.notificationsConfig || loadNotificationConfig();
        } catch {
          // Fall back gracefully if not loaded
        }

        const critRoute = nc?.routes.find(r => r.escalate);
        const criticalAfterS = critRoute?.escalate?.after_s ?? 300;

        return {
          data: {
            thresholds: tc.tiers.map(t => ({ name: t.name, min: t.min })),
            escalation: {
              critical_after_s: criticalAfterS,
            },
            realtime: {
              heartbeat_ms: 15000,
            },
          },
        };
      }
    );
  };
}
