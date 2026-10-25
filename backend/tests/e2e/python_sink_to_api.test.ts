import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { execSync } from 'node:child_process';
import path from 'node:path';
import type { FastifyInstance } from 'fastify';
import type pg from 'pg';
import { createTestPool, TEST_DATABASE_URL } from '../helpers/db.js';
import { buildApp } from '../../src/app.js';
import { loadConfig } from '../../src/config/env.js';
import { PgCamerasRepo } from '../../src/modules/cameras/repo.pg.js';
import { PgEventsRepo } from '../../src/modules/events/repo.pg.js';
import { PgAlertsRepo } from '../../src/modules/alerts/repo.pg.js';
import { PgWatchlistRepo } from '../../src/modules/watchlist/repo.pg.js';
import { PgAnalyticsRepo } from '../../src/modules/analytics/repo.pg.js';
import { PgAuditRepo } from '../../src/common/audit.js';

describe('Cross-language End-to-End: Python Sink -> PostgreSQL -> Fastify REST API', () => {
  let pool: pg.Pool;
  let app: FastifyInstance;

  beforeAll(async () => {
    pool = createTestPool();

    const config = loadConfig({
      NODE_ENV: 'test',
      PORT: '4000',
      DATABASE_URL: TEST_DATABASE_URL,
      SNAPSHOT_DIR: './tests/fixtures/snapshots',
      MJPEG_BASE_URL: 'http://localhost:8001',
    });

    app = await buildApp({
      config,
      camerasRepo: new PgCamerasRepo(pool, config.MJPEG_BASE_URL),
      eventsRepo: new PgEventsRepo(pool),
      alertsRepo: new PgAlertsRepo(pool),
      watchlistRepo: new PgWatchlistRepo(pool),
      analyticsRepo: new PgAnalyticsRepo(pool),
      auditRepo: new PgAuditRepo(pool),
      pool,
      logger: false,
    });
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
    await pool.end();
  });

  it('reads events written by Python into PostgreSQL with exact type and field parity', async () => {
    const scriptPath = path.resolve('./scripts/e2e_seed_test_event.py');
    const pyOutput = execSync(`../.venv/bin/python "${scriptPath}"`, {
      encoding: 'utf-8',
      env: { ...process.env, TEST_DATABASE_URL },
    });

    const match = /EVENT_ID:([a-f0-9-]+)/.exec(pyOutput);
    expect(match).toBeTruthy();
    const eventId = match![1];

    const res = await app.inject({
      method: 'GET',
      url: `/api/events/${eventId}`,
    });

    if (res.statusCode !== 200) {
      console.error('E2E FAILURE BODY:', res.json());
    }

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.event_id).toBe(eventId);
    expect(body.data.camera_id).toBe('E2E-CAM-01');
    expect(body.data.event_type).toBe('ANPR_WATCHLIST_HIT');
    expect(body.data.severity).toBe('HIGH');
    expect(body.data.threat_score).toBe(78);
    expect(body.data.plate).toBe('KA01AB9999');
    expect(body.data.alert).toEqual({
      alert_id: expect.any(String),
      status: 'OPEN',
      priority: 'HIGH',
    });
  });
});
