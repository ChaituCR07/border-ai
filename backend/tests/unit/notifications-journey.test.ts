import { describe, expect, it } from 'vitest';
import { buildJourneySummary, type JourneyDeps } from '../../src/modules/notifications/journey.js';
import { TopologyIndex } from '../../src/modules/correlation/topology.js';
import { loadCorrelationConfig } from '../../src/modules/correlation/config.js';
import { type Sighting } from '../../src/modules/investigation/journey.js';

describe('Journey Summary Integration with Correlation Engine', () => {
  const topo = new TopologyIndex([
    { a: 'CAM-01', b: 'CAM-02', min_s: 180, typical_s: 360, max_s: 720 },
    { a: 'CAM-02', b: 'CAM-04', min_s: 200, typical_s: 420, max_s: 840 },
  ]);
  const config = loadCorrelationConfig();

  const dummySightings: Sighting[] = [
    {
      camera_id: 'CAM-01',
      first_seen: '2026-11-02T10:02:00.000Z',
      last_seen: '2026-11-02T10:02:10.000Z',
      event_count: 1,
      max_score: 50,
      event_types: ['ANPR_MATCH'],
      event_ids: ['e1'],
      plates: ['KA01AB1234'],
    },
    {
      camera_id: 'CAM-02',
      first_seen: '2026-11-02T10:08:00.000Z',
      last_seen: '2026-11-02T10:08:15.000Z',
      event_count: 1,
      max_score: 60,
      event_types: ['ANPR_MATCH'],
      event_ids: ['e2'],
      plates: ['KA01AB1234'],
    },
    {
      camera_id: 'CAM-04',
      first_seen: '2026-11-02T10:15:00.000Z',
      last_seen: '2026-11-02T10:15:10.000Z',
      event_count: 1,
      max_score: 85,
      event_types: ['ANPR_MATCH'],
      event_ids: ['e3'],
      plates: ['KA01AB1234'],
    },
  ];

  it('builds formatted journey text with (this alert) indicator on current camera', async () => {
    const deps: JourneyDeps = {
      getSightings: async () => dummySightings,
      topo,
      config,
      timeoutMs: 1000,
    };

    const res = await buildJourneySummary(
      'KA01AB1234',
      'CAM-04',
      '2026-11-02T10:15:00.000Z',
      deps
    );

    expect(res).not.toBeNull();
    expect(res!.text).toBe('CAM-01 10:02 → CAM-02 10:08 → CAM-04 10:15 (this alert)');
    expect(res!.warnings).toEqual([]);
  });

  it('degrades gracefully and returns null when getSightings times out', async () => {
    const slowDeps: JourneyDeps = {
      getSightings: async () => new Promise(resolve => setTimeout(() => resolve(dummySightings), 100)),
      topo,
      config,
      timeoutMs: 20, // 20ms timeout
    };

    const res = await buildJourneySummary(
      'KA01AB1234',
      'CAM-04',
      '2026-11-02T10:15:00.000Z',
      slowDeps
    );

    expect(res).toBeNull();
  });

  it('returns null when plate is not provided', async () => {
    const deps: JourneyDeps = {
      getSightings: async () => dummySightings,
      topo,
      config,
    };

    const res = await buildJourneySummary(null, 'CAM-04', '2026-11-02T10:15:00.000Z', deps);
    expect(res).toBeNull();
  });
});
