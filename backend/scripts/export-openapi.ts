import fs from 'node:fs';
import path from 'node:path';
import { buildApp } from '../src/app.js';
import { loadConfig } from '../src/config/env.js';
import { InMemoryCamerasRepo } from '../src/modules/cameras/repo.memory.js';
import { InMemoryEventsRepo } from '../src/modules/events/repo.memory.js';
import { InMemoryAlertsRepo } from '../src/modules/alerts/repo.memory.js';
import { InMemoryWatchlistRepo } from '../src/modules/watchlist/repo.memory.js';
import { InMemoryAnalyticsRepo } from '../src/modules/analytics/repo.memory.js';

async function main() {
  const config = loadConfig({ DATABASE_URL: 'postgres://localhost/test' });
  const app = await buildApp({
    config,
    camerasRepo: new InMemoryCamerasRepo('http://localhost:8001'),
    eventsRepo: new InMemoryEventsRepo(),
    alertsRepo: new InMemoryAlertsRepo(),
    watchlistRepo: new InMemoryWatchlistRepo(),
    analyticsRepo: new InMemoryAnalyticsRepo(),
    logger: false,
  });

  await app.ready();
  const swaggerDoc = app.swagger();
  const outPath = path.resolve(process.cwd(), '../docs/api/openapi.json');
  fs.writeFileSync(outPath, JSON.stringify(swaggerDoc, null, 2), 'utf-8');
  console.log(`OpenAPI document generated at: ${outPath}`);
  await app.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
