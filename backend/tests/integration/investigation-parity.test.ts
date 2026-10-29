import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryEventsRepo } from '../../src/modules/events/repo.memory.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';

describe('Investigation Forensic Search Parity & Golden Dataset', () => {
  let app: FastifyInstance;
  let eventsRepo: InMemoryEventsRepo;
  let investigationRepo: InMemoryInvestigationRepo;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    eventsRepo = res.eventsRepo;
    investigationRepo = res.investigationRepo;

    const goldenRows = [
      // 1. Acceptance Journey events
      {
        event_id: '10000000-0000-0000-0000-000000000001',
        camera_id: 'CAM-03',
        event_type: 'VEHICLE_DETECTED',
        threat_score: 50,
        severity: 'MEDIUM' as const,
        timestamp: '2026-10-25T10:00:00.000000Z',
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
        metadata: { vehicle_id: 'VEH-100' },
        snapshot_path: null,
        track_id: null,
      },
      {
        event_id: '10000000-0000-0000-0000-000000000002',
        camera_id: 'CAM-03',
        event_type: 'ANPR_MATCH',
        threat_score: 75,
        severity: 'HIGH' as const,
        timestamp: '2026-10-25T10:00:10.000000Z',
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
        metadata: { vehicle_id: 'VEH-100' },
        snapshot_path: null,
        track_id: null,
      },
      {
        event_id: '10000000-0000-0000-0000-000000000003',
        camera_id: 'CAM-04',
        event_type: 'VEHICLE_DETECTED',
        threat_score: 60,
        severity: 'HIGH' as const,
        timestamp: '2026-10-25T10:00:38.000000Z',
        plate: 'KA0IAB1234', // lookalike
        vehicle_id: 'VEH-100',
        metadata: { vehicle_id: 'VEH-100' },
        snapshot_path: null,
        track_id: null,
      },
      {
        event_id: '10000000-0000-0000-0000-000000000004',
        camera_id: 'CAM-05',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        threat_score: 90,
        severity: 'CRITICAL' as const,
        timestamp: '2026-10-25T10:01:50.000000Z',
        plate: 'KA01AB1234',
        vehicle_id: 'VEH-100',
        metadata: { vehicle_id: 'VEH-100' },
        snapshot_path: null,
        track_id: null,
      },
      // 2. Overnight events for time-of-day window (22:00 -> 05:00 UTC)
      {
        event_id: '30000000-0000-0000-0000-000000000001',
        camera_id: 'CAM-02',
        event_type: 'VEHICLE_DETECTED',
        threat_score: 65,
        severity: 'HIGH' as const,
        timestamp: '2026-10-25T23:30:00.000000Z',
        plate: 'MH12CD5678',
        metadata: {},
        snapshot_path: null,
        track_id: null,
      },
      {
        event_id: '30000000-0000-0000-0000-000000000002',
        camera_id: 'CAM-02',
        event_type: 'VEHICLE_DETECTED',
        threat_score: 40,
        severity: 'MEDIUM' as const,
        timestamp: '2026-10-25T14:00:00.000000Z',
        plate: 'MH12CD5678',
        metadata: {},
        snapshot_path: null,
        track_id: null,
      },
      // 3. Person identifier
      {
        event_id: '40000000-0000-0000-0000-000000000001',
        camera_id: 'CAM-01',
        event_type: 'PERSON_DETECTED',
        threat_score: 85,
        severity: 'HIGH' as const,
        timestamp: '2026-10-25T11:00:00.000000Z',
        person_id: 'PER-1002',
        metadata: { person_id: 'PER-1002' },
        snapshot_path: null,
        track_id: null,
      },
    ];

    await eventsRepo.seed(goldenRows);
    await investigationRepo.seed(goldenRows);
  });

  it('correctly reconstructs acceptance journey CAM-03 -> CAM-04 -> CAM-05 with +28s and +72s gaps', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/investigation/journey?plate=KA01AB1234&from=2026-10-25T00:00:00.000Z&to=2026-10-25T23:59:59.000Z',
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data.sightings).toHaveLength(3);
    expect(body.data.sightings.map((s: any) => s.camera_id)).toEqual(['CAM-03', 'CAM-04', 'CAM-05']);
    expect(body.data.transitions).toEqual([
      { from: 'CAM-03', to: 'CAM-04', gap_s: 28 },
      { from: 'CAM-04', to: 'CAM-05', gap_s: 72 },
    ]);
    expect(body.data.plate_variants).toEqual(['KA01AB1234', 'KA0IAB1234']);
  });

  it('filters night window 22:00 -> 05:00 UTC (wrapping midnight)', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?plate=MH12CD5678&from=2026-10-25T00:00:00.000Z&to=2026-10-26T00:00:00.000Z&time_from=22:00&time_to=05:00&tz=UTC',
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    // Night event at 23:30 is included; daytime event at 14:00 is excluded
    expect(body.data).toHaveLength(1);
    expect(body.data[0].event_id).toBe('30000000-0000-0000-0000-000000000001');
  });

  it('retrieves person events with investigator role and valid purpose', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/events?person_id=PER-1002&purpose=Border+checkpoint+audit+12',
      headers: {
        'x-actor-role': 'INVESTIGATOR',
        'x-actor-id': 'inv-99',
      },
    });
    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(body.data).toHaveLength(1);
    expect(body.data[0].person_id).toBe('PER-1002');
  });
});
