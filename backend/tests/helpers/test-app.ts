import type { FastifyInstance } from 'fastify';
import { buildApp } from '../../src/app.js';
import { loadConfig } from '../../src/config/env.js';
import { InMemoryCamerasRepo } from '../../src/modules/cameras/repo.memory.js';
import { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';
import { InMemoryAlertsRepo } from '../../src/modules/alerts/repo.memory.js';
import { InMemoryWatchlistRepo } from '../../src/modules/watchlist/repo.memory.js';
import { InMemoryAnalyticsRepo } from '../../src/modules/analytics/repo.memory.js';
import { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';
import { InMemoryAuditRepo } from '../../src/common/audit.js';

export async function createTestApp(): Promise<{
  app: FastifyInstance;
  camerasRepo: InMemoryCamerasRepo;
  eventsRepo: InMemoryEventsRepo;
  alertsRepo: InMemoryAlertsRepo;
  watchlistRepo: InMemoryWatchlistRepo;
  analyticsRepo: InMemoryAnalyticsRepo;
  investigationRepo: InMemoryInvestigationRepo;
  auditRepo: InMemoryAuditRepo;
}> {
  const config = loadConfig({
    NODE_ENV: 'test',
    PORT: '4000',
    DATABASE_URL: 'postgres://border_api:test@localhost:5432/border_ai_test',
    SNAPSHOT_DIR: './tests/fixtures/snapshots',
    MJPEG_BASE_URL: 'http://localhost:8001',
  });

  const camerasRepo = new InMemoryCamerasRepo(config.MJPEG_BASE_URL);
  const eventsRepo = new InMemoryEventsRepo();
  const alertsRepo = new InMemoryAlertsRepo();
  const watchlistRepo = new InMemoryWatchlistRepo();
  const analyticsRepo = new InMemoryAnalyticsRepo();
  const investigationRepo = new InMemoryInvestigationRepo(eventsRepo);
  const auditRepo = new InMemoryAuditRepo();

  const app = await buildApp({
    config,
    camerasRepo,
    eventsRepo,
    alertsRepo,
    watchlistRepo,
    analyticsRepo,
    investigationRepo,
    auditRepo,
    logger: false,
  });

  await app.ready();

  return {
    app,
    camerasRepo,
    eventsRepo,
    alertsRepo,
    watchlistRepo,
    analyticsRepo,
    investigationRepo,
    auditRepo,
  };
}
