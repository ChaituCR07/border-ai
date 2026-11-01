import fs from 'node:fs';
import path from 'node:path';
import { buildApp } from '../src/app.js';
import { loadConfig } from '../src/config/env.js';
import { InMemoryCamerasRepo } from '../src/modules/cameras/repo.memory.js';
import { InMemoryEventsRepo } from '../src/modules/events/repo.memory.js';
import { InMemoryAlertsRepo } from '../src/modules/alerts/repo.memory.js';
import { InMemoryWatchlistRepo } from '../src/modules/watchlist/repo.memory.js';
import { InMemoryAnalyticsRepo } from '../src/modules/analytics/repo.memory.js';
import { InMemoryInvestigationRepo } from '../src/modules/investigation/repo.memory.js';
import { MemoryCorrelationRepo } from '../src/modules/correlation/repo.memory.js';
import { InMemoryAuditRepo } from '../src/common/audit.js';

async function main() {
  const config = loadConfig({ DATABASE_URL: 'postgres://localhost/test' });
  const eventsRepo = new InMemoryEventsRepo();
  const investigationRepo = new InMemoryInvestigationRepo(eventsRepo);
  const correlationRepo = new MemoryCorrelationRepo(eventsRepo);
  const auditRepo = new InMemoryAuditRepo();

  const app = await buildApp({
    config,
    camerasRepo: new InMemoryCamerasRepo('http://localhost:8001'),
    eventsRepo,
    alertsRepo: new InMemoryAlertsRepo(),
    watchlistRepo: new InMemoryWatchlistRepo(),
    analyticsRepo: new InMemoryAnalyticsRepo(),
    investigationRepo,
    correlationRepo,
    auditRepo,
    logger: false,
  });

  await app.ready();
  const swaggerDoc = app.swagger();
  const rootDir = fs.existsSync(path.resolve(process.cwd(), 'configs'))
    ? process.cwd()
    : path.resolve(process.cwd(), '..');
  const outPath = path.resolve(rootDir, 'docs/api/openapi.json');
  fs.writeFileSync(outPath, JSON.stringify(swaggerDoc, null, 2), 'utf-8');
  console.log(`OpenAPI document generated at: ${outPath}`);
  await app.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
