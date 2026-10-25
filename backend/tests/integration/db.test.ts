import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { randomUUID } from 'node:crypto';
import type pg from 'pg';
import { createTestPool } from '../helpers/db.js';
import { PgEventsRepo } from '../../src/modules/events/repo.pg.js';
import { PgAlertsRepo } from '../../src/modules/alerts/repo.pg.js';
import { PgCamerasRepo } from '../../src/modules/cameras/repo.pg.js';
import { PgWatchlistRepo } from '../../src/modules/watchlist/repo.pg.js';
import { PgAuditRepo } from '../../src/common/audit.js';

describe('Real PostgreSQL Integration & Race Conditions', () => {
  let pool: pg.Pool;
  let camerasRepo: PgCamerasRepo;
  let eventsRepo: PgEventsRepo;
  let alertsRepo: PgAlertsRepo;
  let watchlistRepo: PgWatchlistRepo;
  let auditRepo: PgAuditRepo;

  beforeAll(async () => {
    pool = createTestPool();
    camerasRepo = new PgCamerasRepo(pool, 'http://localhost:8001');
    eventsRepo = new PgEventsRepo(pool);
    alertsRepo = new PgAlertsRepo(pool);
    watchlistRepo = new PgWatchlistRepo(pool);
    auditRepo = new PgAuditRepo(pool);

    // Clean up test data
    await pool.query("DELETE FROM alerts WHERE event_id IN (SELECT event_id FROM events WHERE camera_id LIKE 'INT-%')");
    await pool.query("DELETE FROM events WHERE camera_id LIKE 'INT-%'");
    await pool.query("DELETE FROM cameras WHERE camera_id LIKE 'INT-%'");
    await pool.query("DELETE FROM watchlist WHERE identifier LIKE 'INT-%'");
  });

  afterAll(async () => {
    await pool.end();
  });

  it('inserts and lists cameras with pg repo', async () => {
    const cam = await camerasRepo.create({
      camera_id: 'INT-CAM-01',
      name: 'Integration Camera 1',
      location_label: 'Perimeter West',
      stream_url: 'rtsp://10.0.0.10:554/live',
      credentials_ref: 'INT_CREDS',
      enabled: true,
    });

    expect(cam.camera_id).toBe('INT-CAM-01');
    const list = await camerasRepo.list({ q: 'INT-CAM' });
    expect(list.some(c => c.camera_id === 'INT-CAM-01')).toBe(true);
  });

  it('performs keyset cursor pagination with microsecond timestamps stably', async () => {
    const eventId1 = randomUUID();
    const eventId2 = randomUUID();
    const ts1 = '2026-10-25 10:00:00.123456+00';
    const ts2 = '2026-10-25 10:00:00.654321+00';

    await pool.query(
      `INSERT INTO events (event_id, camera_id, track_id, event_type, severity, threat_score, timestamp, metadata)
       VALUES ($1, 'INT-CAM-01', 101, 'LINE_CROSSING', 'HIGH', 75, $2::timestamptz, '{}'::jsonb),
              ($3, 'INT-CAM-01', 102, 'LOITERING', 'LOW', 20, $4::timestamptz, '{}'::jsonb)`,
      [eventId1, ts1, eventId2, ts2]
    );

    // Page 1: limit 1
    const page1 = await eventsRepo.list({ cameraId: 'INT-CAM-01' }, 1);
    expect(page1.length).toBe(1);
    expect(page1[0]!.event_id).toBe(eventId2);

    // Page 2: with cursor
    const cursor = { t: page1[0]!.timestamp, id: page1[0]!.event_id };
    const page2 = await eventsRepo.list({ cameraId: 'INT-CAM-01' }, 1, cursor);
    expect(page2.length).toBe(1);
    expect(page2[0]!.event_id).toBe(eventId1);
  });

  it('handles concurrent atomic alert acknowledgement with exactly one winner', async () => {
    const eventId = randomUUID();
    const alertId = randomUUID();

    await pool.query(
      `INSERT INTO events (event_id, camera_id, track_id, event_type, severity, threat_score, timestamp, metadata)
       VALUES ($1, 'INT-CAM-01', 103, 'RESTRICTED_ZONE_ENTRY', 'CRITICAL', 90, now(), '{}'::jsonb)`,
      [eventId]
    );

    await pool.query(
      `INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, status, created_at)
       VALUES ($1, $2, 'INT-CAM-01', 'CRITICAL', 90, 'NEW', now())`,
      [alertId, eventId]
    );

    // 10 concurrent acknowledge calls
    const workers = Array.from({ length: 10 }, (_, i) =>
      alertsRepo.acknowledge(alertId, `worker_${i}`)
    );

    const results = await Promise.all(workers);
    const updatedCount = results.filter(r => r?.updated === true).length;
    const idempotentCount = results.filter(r => r?.updated === false).length;

    expect(updatedCount).toBe(1); // EXACTLY ONE WINNER!
    expect(idempotentCount).toBe(9); // All 9 others received idempotent 200 representation!

    const finalAlert = await alertsRepo.getById(alertId);
    expect(finalAlert?.status).toBe('ACKNOWLEDGED');
    expect(finalAlert?.acknowledged_by).toMatch(/^worker_\d+$/);
  });
});
