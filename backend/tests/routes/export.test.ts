import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';
import type { InMemoryAuditRepo } from '../../src/common/audit.js';

describe('CSV Export Route GET /api/investigation/export.csv', () => {
  let app: FastifyInstance;
  let eventsRepo: InMemoryEventsRepo;
  let auditRepo: InMemoryAuditRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    eventsRepo = res.eventsRepo;
    auditRepo = res.auditRepo;

    await eventsRepo.seed([
      {
        event_id: '11111111-1111-1111-1111-111111111111',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        track_id: '1',
        severity: 'HIGH',
        threat_score: 80,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: 'CAM-01/snap.jpg',
        plate: '=cmd|"/C calc"!A0', // malicious formula injection attempt
        vehicle_id: 'VEH-01',
        person_id: null,
        metadata: {
          explanation: { factors: [{ name: 'speeding', points: 30 }] },
        },
      },
      {
        event_id: '22222222-2222-2222-2222-222222222222',
        camera_id: 'CAM-02',
        event_type: 'ANPR_MATCH',
        track_id: '2',
        severity: 'MEDIUM',
        threat_score: 60,
        timestamp: '2026-10-25T10:05:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        vehicle_id: null,
        person_id: 'PER-42',
        metadata: {},
      },
    ]);
  });

  it('rejects export from OPERATOR with 403 FORBIDDEN', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/export.csv?purpose=Routine+audit',
      headers: {
        'x-actor-id': 'op-1',
        'x-actor-role': 'OPERATOR',
      },
    });
    expect(res.statusCode).toBe(403);
  });

  it('rejects export without purpose or with short purpose with 422 PURPOSE_REQUIRED', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/export.csv',
      headers: {
        'x-actor-id': 'inv-1',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res.statusCode).toBe(422);

    const res2 = await app.inject({
      method: 'GET',
      url: '/api/investigation/export.csv?purpose=test',
      headers: {
        'x-actor-id': 'inv-1',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res2.statusCode).toBe(422);
  });

  it('streams CSV with formula injection protection and writes audit log', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/export.csv?purpose=Investigating+security+incident',
      headers: {
        'x-actor-id': 'inv-1',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toContain('text/csv');
    expect(res.headers['content-disposition']).toContain('attachment');

    const csv = res.payload;
    expect(csv).toContain('timestamp,camera_id,event_type');
    // Verify malicious formula '=' has been sanitized to "'="
    expect(csv).toContain('"\'=cmd|""/C calc""!A0"');
    expect(csv).toContain('KA01AB1234');

    const logs = await auditRepo.list();
    const exportLog = logs.find(l => l.action === 'EXPORT');
    expect(exportLog).toBeDefined();
    expect(exportLog?.actor).toBe('inv-1');
    expect(exportLog?.detail?.purpose).toBe('Investigating security incident');
    expect(exportLog?.detail?.row_count).toBe(2);
  });
});
