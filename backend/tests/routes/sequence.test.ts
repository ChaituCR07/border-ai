import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { MemoryCorrelationRepo } from '../../src/modules/correlation/repo.memory.js';
import type { InMemoryAuditRepo } from '../../src/common/audit.js';

describe('Sequence search GET /api/correlation/sequence', () => {
  let app: FastifyInstance;
  let correlationRepo: MemoryCorrelationRepo;
  let auditRepo: InMemoryAuditRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    correlationRepo = res.correlationRepo;
    auditRepo = res.auditRepo;

    // Seed events into correlationRepo
    correlationRepo.seedEvents([
      // Plate 1: Correct sequence KA01AB1234 (CAM-01 -> CAM-02 -> CAM-04) within 500s each
      {
        event_id: 'e1',
        camera_id: 'CAM-01',
        event_type: 'ANPR_MATCH',
        track_id: '1',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'e2',
        camera_id: 'CAM-02',
        event_type: 'ANPR_MATCH',
        track_id: '2',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:06:00.000000Z', // +360 s
        snapshot_path: null,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'e3',
        camera_id: 'CAM-04',
        event_type: 'ANPR_MATCH',
        track_id: '3',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:13:00.000000Z', // +420 s
        snapshot_path: null,
        plate: 'KA0IAB1234', // lookalike variant
      },

      // Plate 2: Reversed order KA02CD5678 (CAM-04 -> CAM-02 -> CAM-01)
      {
        event_id: 'rev1',
        camera_id: 'CAM-04',
        event_type: 'ANPR_MATCH',
        track_id: '4',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: null,
        plate: 'KA02CD5678',
      },
      {
        event_id: 'rev2',
        camera_id: 'CAM-02',
        event_type: 'ANPR_MATCH',
        track_id: '5',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:07:00.000000Z',
        snapshot_path: null,
        plate: 'KA02CD5678',
      },
      {
        event_id: 'rev3',
        camera_id: 'CAM-01',
        event_type: 'ANPR_MATCH',
        track_id: '6',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:14:00.000000Z',
        snapshot_path: null,
        plate: 'KA02CD5678',
      },

      // Plate 3: Gap exceeded DL01EF9999 (CAM-01 -> CAM-02, but gap is 2000s > 900s)
      {
        event_id: 'gap1',
        camera_id: 'CAM-01',
        event_type: 'ANPR_MATCH',
        track_id: '7',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: null,
        plate: 'DL01EF9999',
      },
      {
        event_id: 'gap2',
        camera_id: 'CAM-02',
        event_type: 'ANPR_MATCH',
        track_id: '8',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:40:00.000000Z', // +2400 s
        snapshot_path: null,
        plate: 'DL01EF9999',
      },
      {
        event_id: 'gap3',
        camera_id: 'CAM-04',
        event_type: 'ANPR_MATCH',
        track_id: '9',
        severity: 'LOW',
        threat_score: 30,
        timestamp: '2026-10-25T10:45:00.000000Z',
        snapshot_path: null,
        plate: 'DL01EF9999',
      },
    ]);
  });

  it('matches ordered sequence of cameras and includes look-alike variants', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02,CAM-04&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&max_hop_gap_s=900&purpose=Cross-border%20convoy%20inquiry',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data).toHaveLength(1);
    expect(body.data[0].representative_plate).toBe('KA01AB1234');
    expect(body.data[0].plate_key).toBe('KA01A81234');
    expect(body.data[0].plate_variants).toContain('KA0IAB1234');
    expect(body.data[0].hops).toHaveLength(3);
    expect(body.data[0].hops[0].camera_id).toBe('CAM-01');
    expect(body.data[0].hops[1].camera_id).toBe('CAM-02');
    expect(body.data[0].hops[2].camera_id).toBe('CAM-04');
    expect(body.data[0].total_duration_s).toBe(780); // 13m = 780s
  });

  it('excludes vehicles travelling in reverse order and vehicles exceeding max hop gap', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02,CAM-04&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&max_hop_gap_s=900&purpose=Investigation%20ABC',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });

    expect(res.statusCode).toBe(200);
    const plates = res.json().data.map((m: any) => m.plate_key);
    expect(plates).not.toContain('KA02CD5678');
    expect(plates).not.toContain('DL01EF9999');
  });

  it('enforces RBAC: Investigator and Admin allowed, Operator and Viewer rejected with 403', async () => {
    const operatorRes = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=Investigation%20XYZ',
      headers: {
        'x-actor-role': 'OPERATOR',
        'x-actor-id': 'op-1',
      },
    });
    expect(operatorRes.statusCode).toBe(403);

    const viewerRes = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=Investigation%20XYZ',
      headers: {
        'x-actor-role': 'VIEWER',
        'x-actor-id': 'view-1',
      },
    });
    expect(viewerRes.statusCode).toBe(403);
  });

  it('rejects missing or short purpose (< 5 chars) with 400/422', async () => {
    const noPurposeRes = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });
    expect([400, 422]).toContain(noPurposeRes.statusCode);

    const shortPurposeRes = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=abc',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });
    expect([400, 422]).toContain(shortPurposeRes.statusCode);
  });

  it('rejects step count < 2 or > 5 with 400', async () => {
    const singleStepRes = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=Valid%20purpose',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });
    expect(singleStepRes.statusCode).toBe(400);

    const sixStepsRes = await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=C1,C2,C3,C4,C5,C6&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=Valid%20purpose',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });
    expect(sixStepsRes.statusCode).toBe(400);
  });

  it('rejects camera IDs with SQL injection or invalid chars', async () => {
    const injectRes = await app.inject({
      method: 'GET',
      url: "/api/correlation/sequence?cams=CAM-01,CAM-02';DROP%20TABLE%20events;--&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=Valid%20purpose",
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });
    expect(injectRes.statusCode).toBe(400);
  });

  it('records audit log entry for SEQUENCE_SEARCH with parameters and purpose', async () => {
    const initialAudits = (await auditRepo.list()).length;

    await app.inject({
      method: 'GET',
      url: '/api/correlation/sequence?cams=CAM-01,CAM-02,CAM-04&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z&purpose=Narcotics%20convoy%20intel',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-1',
      },
    });

    const entries = await auditRepo.list();
    expect(entries.length).toBe(initialAudits + 1);
    const entry = entries[0]!;
    expect(entry.action).toBe('SEQUENCE_SEARCH');
    expect(entry.actor).toBe('inv-1');
    expect(entry.detail?.purpose).toBe('Narcotics convoy intel');
    expect(entry.detail?.cams).toEqual(['CAM-01', 'CAM-02', 'CAM-04']);
  });
});
