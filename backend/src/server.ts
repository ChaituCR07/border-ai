import Redis from 'ioredis';
import { loadConfig } from './config/env.js';
import { createPool } from './db/pool.js';
import { PgCamerasRepo } from './modules/cameras/repo.pg.js';
import { PgEventsRepo } from './modules/events/repo.pg.js';
import { PgAlertsRepo } from './modules/alerts/repo.pg.js';
import { PgWatchlistRepo } from './modules/watchlist/repo.pg.js';
import { PgAnalyticsRepo } from './modules/analytics/repo.pg.js';
import { PgInvestigationRepo } from './modules/investigation/repo.pg.js';
import { PgAuditRepo } from './common/audit.js';
import { Hub } from './realtime/hub.js';
import { AlertHydrator } from './realtime/hydrator.js';
import { AlertStreamConsumer } from './realtime/alert-stream-consumer.js';
import { parseAlertEnvelope } from './realtime/envelope.js';
import { buildApp } from './app.js';

async function bootstrap() {
  const config = loadConfig();

  if (config.NODE_ENV === 'production') {
    throw new Error('Production deployment requires real JWT auth provider (scheduled for Day 26).');
  }

  const pool = createPool(config.DATABASE_URL);
  const redis = new Redis(config.REDIS_URL, {
    maxRetriesPerRequest: null,
    retryStrategy: (times) => Math.min(times * 100, 3000),
  });

  const camerasRepo = new PgCamerasRepo(pool, config.MJPEG_BASE_URL);
  const eventsRepo = new PgEventsRepo(pool);
  const alertsRepo = new PgAlertsRepo(pool);
  const watchlistRepo = new PgWatchlistRepo(pool);
  const analyticsRepo = new PgAnalyticsRepo(pool);
  const investigationRepo = new PgInvestigationRepo(pool);
  const auditRepo = new PgAuditRepo(pool);

  const hub = new Hub({
    maxClients: 200,
    maxBufferedBytes: 1024 * 1024,
    heartbeatMs: 15_000,
  });

  const hydrator = new AlertHydrator(alertsRepo);

  const consumer = new AlertStreamConsumer(
    redis,
    async (_id, fields) => {
      const env = parseAlertEnvelope(fields);
      if (!env) return;

      // Deduplicate repeat broadcasts from engine retries
      if (hydrator.isDuplicate(env.alert_id)) {
        return;
      }

      const alert = await hydrator.hydrate(env);
      hub.broadcastState({
        v: 1,
        type: 'alert.created',
        data: { alert },
      });
    },
    {
      stream: 'surveillance.alerts',
      startId: '$',
      blockMs: 5000,
      onResyncRequired: (reason) => {
        hub.broadcastState({
          v: 1,
          type: 'resync_required',
          reason,
        });
      },
    }
  );

  const app = await buildApp({
    config,
    camerasRepo,
    eventsRepo,
    alertsRepo,
    watchlistRepo,
    analyticsRepo,
    investigationRepo,
    auditRepo,
    pool,
    hub,
    consumer,
    logger: {
      level: 'debug',
    },
  });

  // Start background stream tail consumer
  consumer.run().catch((err) => {
    app.log.error(err, 'Alert stream consumer fatal failure');
  });

  const stop = async () => {
    app.log.info('Shutting down server...');
    consumer.stop();
    hub.stop();
    await app.close();
    await pool.end();
    redis.disconnect();
    process.exit(0);
  };

  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);

  try {
    await app.listen({ port: config.PORT, host: config.HOST });
    console.log(`Border-AI REST API listening on http://${config.HOST}:${config.PORT}`);
    console.log(`WebSocket Gateway available at ws://${config.HOST}:${config.PORT}/api/ws`);
    console.log(`Swagger UI Documentation available at http://${config.HOST}:${config.PORT}/docs`);
  } catch (err) {
    app.log.error(err);
    consumer.stop();
    hub.stop();
    await pool.end();
    redis.disconnect();
    process.exit(1);
  }
}

if (process.env.NODE_ENV !== 'test') {
  bootstrap().catch((err) => {
    console.error('Fatal bootstrap error:', err);
    process.exit(1);
  });
}
