import Fastify, { type FastifyInstance } from 'fastify';
import { randomUUID } from 'node:crypto';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
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

import { cameraRoutes } from './modules/cameras/routes.js';
import type { CamerasRepo } from './modules/cameras/repo.js';

import { eventRoutes } from './modules/events/routes.js';
import type { EventsRepo } from './modules/events/repo.js';

import { alertRoutes } from './modules/alerts/routes.js';
import type { AlertsRepo } from './modules/alerts/repo.js';
import type { AlertChangeCallback } from './modules/alerts/service.js';

import { watchlistRoutes } from './modules/watchlist/routes.js';
import type { WatchlistRepo } from './modules/watchlist/repo.js';

import { analyticsRoutes } from './modules/analytics/routes.js';
import type { AnalyticsRepo } from './modules/analytics/repo.js';

import { snapshotRoutes } from './modules/snapshots/routes.js';
import { healthRoutes } from './modules/health/routes.js';

export interface AppDeps {
  config: Config;
  camerasRepo: CamerasRepo;
  eventsRepo: EventsRepo;
  alertsRepo: AlertsRepo;
  watchlistRepo: WatchlistRepo;
  analyticsRepo: AnalyticsRepo;
  auditRepo?: AuditRepo;
  pool?: pg.Pool;
  logger?: boolean | Record<string, unknown>;
  onAlertChanged?: AlertChangeCallback;
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

  // Security Headers
  await app.register(helmet, {
    contentSecurityPolicy: false, // Allows Swagger UI to render smoothly
  });

  // CORS
  await app.register(cors, {
    origin: deps.config.corsOrigins,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    credentials: true,
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
        description: 'REST API exposing cameras, events, alerts, watchlist, and analytics from PostgreSQL',
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

  // Root & Health routes
  await app.register(healthRoutes({ pool: deps.pool }), { prefix: '/api' });

  // Main API namespace with authentication seam
  await app.register(
    async (api) => {
      api.addHook('preHandler', authenticate);

      await api.register(cameraRoutes({ camerasRepo: deps.camerasRepo, auditRepo: deps.auditRepo }));
      await api.register(eventRoutes({ eventsRepo: deps.eventsRepo, snapshotDir: deps.config.SNAPSHOT_DIR }));
      await api.register(
        alertRoutes({
          alertsRepo: deps.alertsRepo,
          auditRepo: deps.auditRepo,
          onAlertChanged: deps.onAlertChanged,
        })
      );
      await api.register(watchlistRoutes({ watchlistRepo: deps.watchlistRepo, auditRepo: deps.auditRepo }));
      await api.register(analyticsRoutes({ analyticsRepo: deps.analyticsRepo }));
      await api.register(snapshotRoutes({ snapshotDir: deps.config.SNAPSHOT_DIR }));
    },
    { prefix: '/api' }
  );

  return app;
}
