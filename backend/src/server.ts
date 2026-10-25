import { loadConfig } from './config/env.js';
import { createPool } from './db/pool.js';
import { PgCamerasRepo } from './modules/cameras/repo.pg.js';
import { PgEventsRepo } from './modules/events/repo.pg.js';
import { PgAlertsRepo } from './modules/alerts/repo.pg.js';
import { PgWatchlistRepo } from './modules/watchlist/repo.pg.js';
import { PgAnalyticsRepo } from './modules/analytics/repo.pg.js';
import { PgAuditRepo } from './common/audit.js';
import { buildApp } from './app.js';

async function bootstrap() {
  const config = loadConfig();

  if (config.NODE_ENV === 'production') {
    throw new Error('Production deployment requires real JWT auth provider (scheduled for Day 26).');
  }

  const pool = createPool(config.DATABASE_URL);

  const camerasRepo = new PgCamerasRepo(pool, config.MJPEG_BASE_URL);
  const eventsRepo = new PgEventsRepo(pool);
  const alertsRepo = new PgAlertsRepo(pool);
  const watchlistRepo = new PgWatchlistRepo(pool);
  const analyticsRepo = new PgAnalyticsRepo(pool);
  const auditRepo = new PgAuditRepo(pool);

  const app = await buildApp({
    config,
    camerasRepo,
    eventsRepo,
    alertsRepo,
    watchlistRepo,
    analyticsRepo,
    auditRepo,
    pool,
    logger: {
      level: 'debug',
    },
  });

  const stop = async () => {
    app.log.info('Shutting down server...');
    await app.close();
    await pool.end();
    process.exit(0);
  };

  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);

  try {
    await app.listen({ port: config.PORT, host: config.HOST });
    console.log(`Border-AI REST API listening on http://${config.HOST}:${config.PORT}`);
    console.log(`Swagger UI Documentation available at http://${config.HOST}:${config.PORT}/docs`);
  } catch (err) {
    app.log.error(err);
    await pool.end();
    process.exit(1);
  }
}

if (process.env.NODE_ENV !== 'test') {
  bootstrap().catch((err) => {
    console.error('Fatal bootstrap error:', err);
    process.exit(1);
  });
}
