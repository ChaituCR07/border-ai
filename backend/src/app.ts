import Fastify, { type FastifyInstance } from 'fastify';
import { randomUUID } from 'node:crypto';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import websocket from '@fastify/websocket';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import {
  serializerCompiler,
  validatorCompiler,
  jsonSchemaTransform,
  type ZodTypeProvider,
} from 'fastify-type-provider-zod';
import type pg from 'pg';

import type { Config } from './config/env.js';
import { errorHandler } from './common/errors.js';
import { authenticate } from './common/auth.js';
import type { AuditRepo } from './common/audit.js';

import { Hub } from './realtime/hub.js';
import { wsRoutes } from './realtime/ws-route.js';
import type { AlertStreamConsumer } from './realtime/alert-stream-consumer.js';

import { cameraRoutes } from './modules/cameras/routes.js';
import type { CamerasRepo } from './modules/cameras/repo.js';

import { eventRoutes } from './modules/events/routes.js';
import type { EventsRepo } from './modules/events/repo.js';

import { alertRoutes } from './modules/alerts/routes.js';
import type { AlertsRepo } from './modules/alerts/repo.js';
import type { AlertChangeCallback } from './modules/alerts/service.js';
import type { AlertResource } from './types/domain.js';

import { watchlistRoutes } from './modules/watchlist/routes.js';
import type { WatchlistRepo } from './modules/watchlist/repo.js';

import { analyticsRoutes } from './modules/analytics/routes.js';
import type { AnalyticsRepo } from './modules/analytics/repo.js';

import { snapshotRoutes } from './modules/snapshots/routes.js';
import { healthRoutes } from './modules/health/routes.js';

import { investigationRoutes } from './modules/investigation/routes.js';
import type { InvestigationRepo } from './modules/investigation/repo.js';

import { correlationRoutes } from './modules/correlation/routes.js';
import type { CorrelationRepo } from './modules/correlation/repo.js';
import { MemoryCorrelationRepo } from './modules/correlation/repo.memory.js';
import { PgCorrelationRepo } from './modules/correlation/repo.pg.js';

import { configRoutes } from './modules/config/routes.js';
import { notificationRoutes } from './modules/notifications/routes.js';
import { NotificationsRepo } from './modules/notifications/repo.js';
import type { NotificationPlanner } from './modules/notifications/planner.js';
import type { NotificationWorker } from './modules/notifications/worker.js';

export interface AppDeps {
  config: Config;
  camerasRepo: CamerasRepo;
  eventsRepo: EventsRepo;
  alertsRepo: AlertsRepo;
  watchlistRepo: WatchlistRepo;
  analyticsRepo: AnalyticsRepo;
  investigationRepo?: InvestigationRepo;
  correlationRepo?: CorrelationRepo;
  notificationsRepo?: NotificationsRepo;
  planner?: NotificationPlanner;
  worker?: NotificationWorker;
  auditRepo?: AuditRepo;
  pool?: pg.Pool;
  logger?: boolean | Record<string, unknown>;
  onAlertChanged?: AlertChangeCallback;
  hub?: Hub;
  consumer?: AlertStreamConsumer;
}

export async function buildApp(deps: AppDeps): Promise<FastifyInstance> {
  const app = Fastify({
    logger: deps.logger ?? false,
    genReqId: () => randomUUID(),
    ajv: {
      customOptions: {
        removeAdditional: false,
      },
    },
  }).withTypeProvider<ZodTypeProvider>();

  app.setValidatorCompiler(validatorCompiler);
  app.setSerializerCompiler(serializerCompiler);
  app.setErrorHandler(errorHandler);

  const hub =
    deps.hub ??
    new Hub({
      maxClients: 200,
      maxBufferedBytes: 1024 * 1024,
      heartbeatMs: 15_000,
      log: app.log,
    });

  hub.start();

  app.addHook('onClose', async () => {
    deps.planner?.stop();
    deps.worker?.stop();
    hub.stop();
  });

  // Security Headers
  await app.register(helmet, {
    contentSecurityPolicy: false,
  });

  // CORS
  await app.register(cors, {
    origin: deps.config.corsOrigins,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    credentials: true,
  });

  // WebSocket support
  await app.register(websocket, {
    options: {
      maxPayload: 1024,
    },
  });

  // Rate Limiting
  await app.register(rateLimit, {
    max: 300,
    timeWindow: '1 minute',
  });

  // OpenAPI Documentation
  await app.register(swagger, {
    openapi: {
      info: {
        title: 'Border-AI Video Intelligence Platform API',
        description: 'REST API exposing cameras, events, alerts, watchlist, analytics, and investigation workbench',
        version: '0.3.0',
      },
      servers: [
        {
          url: `http://${deps.config.HOST}:${deps.config.PORT}`,
          description: 'Local development server',
        },
      ],
      tags: [
        { name: 'Cameras', description: 'Camera inventory, credentials references, and live MJPEG streaming' },
        { name: 'Events', description: 'Video analytics events with keyset pagination and threat explanation' },
        { name: 'Alerts', description: 'Threat alert feed with idempotent, race-safe acknowledgement' },
        { name: 'Investigation', description: 'Forensic search, disjunctive facets, suggest, context, and journey' },
        { name: 'Watchlist', description: 'Strictly non-biometric vehicle and person watchlist management' },
        { name: 'Analytics', description: 'Aggregated time-series, operational camera metrics, and threat histograms' },
        { name: 'Health', description: 'Liveness and database readiness probes' },
      ],
    },
    transform: jsonSchemaTransform,
  });

  await app.register(swaggerUi, {
    routePrefix: '/docs',
    uiConfig: {
      docExpansion: 'list',
      deepLinking: true,
    },
  });

  // Export openapi.json route
  app.get('/openapi.json', async (_req, reply) => {
    return reply.send(app.swagger());
  });

  // Correlation ID Header
  app.addHook('onSend', async (req, reply) => {
    reply.header('x-request-id', req.id);
  });

  // Health routes
  await app.register(healthRoutes({ pool: deps.pool }), { prefix: '/api' });

  // Public system configuration routes (/api/config/public)
  await app.register(configRoutes(), { prefix: '/api' });

  // WebSocket & Realtime Status Routes (/api/ws, /api/realtime/status)
  await app.register(wsRoutes({ hub, config: deps.config, consumer: deps.consumer }), { prefix: '/api' });

  // Alert acknowledgement broadcast hook
  const handleAlertChanged: AlertChangeCallback = (alert: AlertResource) => {
    hub.broadcastState({
      v: 1,
      type: 'alert.updated',
      data: {
        alert: {
          alert_id: alert.alert_id,
          event_id: alert.event_id,
          priority: alert.priority,
          status: alert.status,
          acknowledged_by: alert.acknowledged_by,
          acknowledged_at: alert.acknowledged_at,
          created_at: alert.created_at,
          persisted: true,
          event: {
            camera_id: alert.event.camera_id,
            event_type: alert.event.event_type,
            threat_score: alert.event.threat_score,
            plate: alert.event.plate ?? null,
            timestamp: alert.created_at,
            snapshot_url: alert.event.snapshot_url,
            snapshot_available: Boolean(alert.event.snapshot_url),
          },
        },
      },
    });
    deps.planner?.kick();
    deps.onAlertChanged?.(alert);
  };

  const notificationsRepo =
    deps.notificationsRepo ??
    (deps.pool ? new NotificationsRepo(deps.pool) : new NotificationsRepo({} as any));

  // Main API namespace with authentication seam
  await app.register(
    async (api) => {
      api.addHook('preHandler', authenticate);

      await api.register(cameraRoutes({ camerasRepo: deps.camerasRepo, auditRepo: deps.auditRepo }));
      await api.register(
        eventRoutes({
          eventsRepo: deps.eventsRepo,
          snapshotDir: deps.config.SNAPSHOT_DIR,
          auditRepo: deps.auditRepo,
        })
      );
      await api.register(
        alertRoutes({
          alertsRepo: deps.alertsRepo,
          auditRepo: deps.auditRepo,
          onAlertChanged: handleAlertChanged,
        })
      );
      const correlationRepo =
        deps.correlationRepo ??
        (deps.pool ? new PgCorrelationRepo(deps.pool) : new MemoryCorrelationRepo());

      if (deps.investigationRepo) {
        await api.register(
          investigationRoutes({
            investigationRepo: deps.investigationRepo,
            eventsRepo: deps.eventsRepo,
            auditRepo: deps.auditRepo,
            correlationRepo,
          })
        );
      }

      await api.register(
        correlationRoutes({
          correlationRepo,
          auditRepo: deps.auditRepo,
        })
      );

      await api.register(watchlistRoutes({ watchlistRepo: deps.watchlistRepo, auditRepo: deps.auditRepo }));
      await api.register(analyticsRoutes({ analyticsRepo: deps.analyticsRepo }));
      await api.register(snapshotRoutes({ snapshotDir: deps.config.SNAPSHOT_DIR }));
      await api.register(
        notificationRoutes({
          repo: notificationsRepo,
          planner: deps.planner,
          worker: deps.worker,
          auditRepo: deps.auditRepo,
          enabled: deps.config.NOTIFICATIONS_ENABLED,
          dryRun: deps.config.NOTIFICATIONS_DRY_RUN,
        })
      );
    },
    { prefix: '/api' }
  );

  return app;
}
