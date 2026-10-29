import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';
import type { InMemoryAuditRepo } from '../../src/common/audit.js';

describe('Investigation Audit Logging & Role Gating', () => {
  let app: FastifyInstance;
  let eventsRepo: InMemoryEventsRepo;
  let investigationRepo: InMemoryInvestigationRepo;
  let auditRepo: InMemoryAuditRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    eventsRepo = res.eventsRepo;
    investigationRepo = res.investigationRepo;
    auditRepo = res.auditRepo;

    await eventsRepo.seed([
      {
        event_id: '11111111-1111-1111-1111-111111111111',
        camera_id: 'CAM-01',
        event_type: 'PERSON_DETECTED',
        track_id: '1',
        severity: 'LOW',
        threat_score: 20,
        timestamp: '2026-10-25T10:00:00.000000Z',
        snapshot_path: null,
        person_id: 'PER-100',
        metadata: { person_id: 'PER-100' },
      },
      {
        event_id: '22222222-2222-2222-2222-222222222222',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        track_id: '2',
        severity: 'MEDIUM',
        threat_score: 45,
        timestamp: '2026-10-25T10:05:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        metadata: {},
      },
    ]);

    await investigationRepo.seed([
      {
        event_id: '22222222-2222-2222-2222-222222222222',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        track_id: '2',
        severity: 'MEDIUM',
        threat_score: 45,
        timestamp: '2026-10-25T10:05:00.000000Z',
        snapshot_path: null,
        plate: 'KA01AB1234',
        metadata: {},
      },
    ]);
  });

  it('records audit log on sensitive plate search', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?plate=KA01AB1234',
      headers: {
        'x-actor-id': 'agent-007',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res.statusCode).toBe(200);

    const logs = await auditRepo.list();
    const searchLog = logs.find(l => l.action === 'SEARCH' && l.entity_id === 'KA01AB1234');
    expect(searchLog).toBeDefined();
    expect(searchLog?.actor).toBe('agent-007');
    expect(searchLog?.entity_type).toBe('plate');
    expect(searchLog?.detail?.actor_role).toBe('INVESTIGATOR');
  });

  it('rejects person search from OPERATOR with 403 FORBIDDEN', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?person_id=PER-100&purpose=Routine+investigation',
      headers: {
        'x-actor-id': 'op-01',
        'x-actor-role': 'OPERATOR',
      },
    });
    expect(res.statusCode).toBe(403);
    const body = res.json();
    expect(body.error.code).toBe('FORBIDDEN');
  });

  it('rejects person search without purpose with 422 PURPOSE_REQUIRED', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?person_id=PER-100',
      headers: {
        'x-actor-id': 'inv-01',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res.statusCode).toBe(422);
    const body = res.json();
    expect(body.error.code).toBe('PURPOSE_REQUIRED');
  });

  it('accepts person search from INVESTIGATOR with valid purpose and logs audit entry', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?person_id=PER-100&purpose=Incident+review+case+402',
      headers: {
        'x-actor-id': 'inv-01',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res.statusCode).toBe(200);

    const logs = await auditRepo.list();
    const personLog = logs.find(l => l.action === 'SEARCH' && l.entity_type === 'person');
    expect(personLog).toBeDefined();
    expect(personLog?.actor).toBe('inv-01');
    expect(personLog?.entity_id).toBe('PER-100');
    expect(personLog?.detail?.purpose).toBe('Incident review case 402');
  });

  it('records audit log on journey query', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234',
      headers: {
        'x-actor-id': 'inv-02',
        'x-actor-role': 'INVESTIGATOR',
      },
    });
    expect(res.statusCode).toBe(200);

    const logs = await auditRepo.list();
    const journeyLog = logs.find(l => l.action === 'JOURNEY');
    expect(journeyLog).toBeDefined();
    expect(journeyLog?.actor).toBe('inv-02');
    expect(journeyLog?.entity_id).toBe('KA01AB1234');
    expect(journeyLog?.entity_type).toBe('plate');
  });
});
