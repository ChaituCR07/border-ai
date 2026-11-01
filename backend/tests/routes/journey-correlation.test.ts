import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';
import type { MemoryCorrelationRepo } from '../../src/modules/correlation/repo.memory.js';
import type { InMemoryAuditRepo } from '../../src/common/audit.js';

describe('Journey correlation GET /api/investigation/journey', () => {
  let app: FastifyInstance;
  let repo: InMemoryInvestigationRepo;
  let correlationRepo: MemoryCorrelationRepo;
  let auditRepo: InMemoryAuditRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.investigationRepo;
    correlationRepo = res.correlationRepo;
    auditRepo = res.auditRepo;

    // Seed events for CAM-01 -> CAM-02 -> CAM-04 journey
    await repo.seed([
      {
        event_id: 'e1',
        camera_id: 'CAM-01',
        event_type: 'ANPR_MATCH',
        track_id: '1',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:02:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
      {
        event_id: 'e2',
        camera_id: 'CAM-02',
        event_type: 'ANPR_MATCH',
        track_id: '2',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:08:00.000000Z', // +360 s
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
      {
        event_id: 'e3',
        camera_id: 'CAM-04',
        event_type: 'ANPR_MATCH',
        track_id: '3',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:15:00.000000Z', // +420 s
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
      {
        event_id: 'e4',
        camera_id: 'CAM-05',
        event_type: 'ANPR_MATCH',
        track_id: '4',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:30:00.000000Z', // later event
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
      },
    ]);
  });

  it('returns correlation block with trips and links by default', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-user-role': 'operator',
        'x-user-id': 'op-1',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data).toHaveProperty('correlation');
    expect(body.data.correlation).toHaveProperty('topology_version');
    expect(body.data.correlation.trips.length).toBeGreaterThan(0);
    expect(body.data).toHaveProperty('journey');
    expect(body.data).toHaveProperty('sightings');
  });

  it('filters out later events when end_at parameter is provided', async () => {
    // Only include up to 10:15:00 (exclude 10:30:00 at CAM-05)
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&end_at=2026-10-25T10:16:00.000Z',
      headers: {
        'x-user-role': 'operator',
        'x-user-id': 'op-1',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.sightings).toHaveLength(3);
    const cams = body.data.sightings.map((s: any) => s.camera_id);
    expect(cams).toEqual(['CAM-01', 'CAM-02', 'CAM-04']);
    expect(cams).not.toContain('CAM-05');
  });

  it('omits correlation block when correlate=false', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&correlate=false',
      headers: {
        'x-user-role': 'operator',
        'x-user-id': 'op-1',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.correlation).toBeUndefined();
    expect(body.data.journey).toBeDefined();
    expect(body.data.sightings).toHaveLength(4);
  });

  it('enforces RBAC: Viewer returns 403, Operator returns 200', async () => {
    const viewerRes = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-actor-role': 'VIEWER',
        'x-actor-id': 'view-1',
      },
    });
    expect(viewerRes.statusCode).toBe(403);

    const operatorRes = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-actor-role': 'OPERATOR',
        'x-actor-id': 'op-1',
      },
    });
    expect(operatorRes.statusCode).toBe(200);
  });

  it('serves identical second request from cache while recording audit each time', async () => {
    const initialAudits = (await auditRepo.list()).length;

    const res1 = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-actor-role': 'OPERATOR',
        'x-actor-id': 'op-1',
      },
    });
    expect(res1.statusCode).toBe(200);

    const res2 = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-actor-role': 'OPERATOR',
        'x-actor-id': 'op-1',
      },
    });
    expect(res2.statusCode).toBe(200);
    expect(res2.json()).toEqual(res1.json());

    // Both requests must have an audit log entry
    const finalAudits = (await auditRepo.list()).length;
    expect(finalAudits).toBe(initialAudits + 2);
  });

  it('returns warnings in meta when topology has no links', async () => {
    await correlationRepo.seedTopology({}, []);

    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-user-role': 'operator',
        'x-user-id': 'op-1',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.meta.warnings).toContain('no topology configured');
  });
});
