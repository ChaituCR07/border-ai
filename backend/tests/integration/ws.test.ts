import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { WebSocket } from 'ws';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import { Hub } from '../../src/realtime/hub.js';
import { buildApp } from '../../src/app.js';
import { loadConfig } from '../../src/config/env.js';
import { InMemoryCamerasRepo } from '../../src/modules/cameras/repo.memory.js';
import { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';
import { InMemoryAlertsRepo } from '../../src/modules/alerts/repo.memory.js';
import { InMemoryWatchlistRepo } from '../../src/modules/watchlist/repo.memory.js';
import { InMemoryAnalyticsRepo } from '../../src/modules/analytics/repo.memory.js';
import { InMemoryAuditRepo } from '../../src/common/audit.js';
import { WS_CLOSE } from '@border-ai/protocol';

describe('WebSocket Gateway Integration Tests (/api/ws)', () => {
  let app: FastifyInstance;
  let hub: Hub;
  let port: number;

  beforeAll(async () => {
    hub = new Hub({ heartbeatMs: 60_000 });
    const config = loadConfig({
      NODE_ENV: 'test',
      PORT: '0',
      DATABASE_URL: 'postgres://border_api:test@localhost:5432/border_ai_test',
      SNAPSHOT_DIR: './tests/fixtures/snapshots',
      MJPEG_BASE_URL: 'http://localhost:8001',
    });

    app = await buildApp({
      config,
      hub,
      camerasRepo: new InMemoryCamerasRepo(config.MJPEG_BASE_URL),
      eventsRepo: new InMemoryEventsRepo(),
      alertsRepo: new InMemoryAlertsRepo(),
      watchlistRepo: new InMemoryWatchlistRepo(),
      analyticsRepo: new InMemoryAnalyticsRepo(),
      auditRepo: new InMemoryAuditRepo(),
      logger: false,
    });

    await app.listen({ port: 0, host: '127.0.0.1' });
    const addr = app.server.address();
    port = typeof addr === 'object' && addr ? addr.port : 0;
  });

  afterAll(async () => {
    await app.close();
  });

  const getWsUrl = () => `ws://127.0.0.1:${port}/api/ws`;

  it('rejects connection when Origin is from an unauthorized domain with 403', async () => {
    const ws = new WebSocket(getWsUrl(), {
      headers: { Origin: 'https://malicious-attacker.com' },
    });

    const [err] = await Promise.race([
      new Promise<[Error]>((resolve) => ws.on('error', (e) => resolve([e]))),
      new Promise<[never]>((_, reject) => ws.on('open', () => reject(new Error('Should not have opened')))),
    ]);

    expect(err).toBeDefined();
    expect(err.message).toMatch(/403|Unexpected server response/);
  });

  it('successfully connects with authorized Origin and receives initial hello message', async () => {
    const ws = new WebSocket(getWsUrl(), {
      headers: { Origin: 'http://localhost:5173' },
    });

    const msg = await new Promise<any>((resolve, reject) => {
      ws.on('message', (raw) => resolve(JSON.parse(raw.toString())));
      ws.on('error', reject);
    });

    expect(msg.type).toBe('hello');
    expect(msg.server_epoch).toBe(hub.epoch);
    expect(msg.seq).toBe(hub.currentSeq);
    expect(msg.server_time).toBeDefined();

    ws.close();
  });

  it('responds with heartbeat when client sends ping message', async () => {
    const ws = new WebSocket(getWsUrl(), {
      headers: { Origin: 'http://localhost:5173' },
    });

    // Wait for hello first
    await new Promise((resolve) => ws.once('message', resolve));

    // Send ping
    ws.send(JSON.stringify({ v: 1, type: 'ping' }));

    const reply = await new Promise<any>((resolve) => {
      ws.once('message', (raw) => resolve(JSON.parse(raw.toString())));
    });

    expect(reply.type).toBe('heartbeat');
    expect(reply.seq).toBe(hub.currentSeq);

    ws.close();
  });

  it('closes connection with 1009 when client payload exceeds 1024 bytes', async () => {
    const ws = new WebSocket(getWsUrl(), {
      headers: { Origin: 'http://localhost:5173' },
    });

    await new Promise((resolve) => ws.once('message', resolve));

    // Send payload > 1024 bytes
    const giantPayload = 'A'.repeat(2048);
    ws.send(giantPayload);

    const closeEvent = await new Promise<{ code: number; reason: string }>((resolve) => {
      ws.on('close', (code, reason) => resolve({ code, reason: reason.toString() }));
    });

    expect(closeEvent.code).toBe(WS_CLOSE.TOO_BIG);
  });
});
