import { describe, it, expect } from 'vitest';
import { TopologyIndex, CameraLink } from '../../src/modules/correlation/topology.js';
import { CorrelationConfig } from '../../src/modules/correlation/config.js';
import { correlate } from '../../src/modules/correlation/correlate.js';
import { Sighting } from '../../src/modules/investigation/journey.js';

describe('correlate', () => {
  const cfg: CorrelationConfig = {
    version: 1,
    merge_gap_s: 120,
    trip_break_s: 21600, // 6 hours
    speed_tolerance: 0.8,
    overlap_tolerance_s: 5,
    max_trajectories: 4,
    min_link_confidence: 0.3,
    plate_conf: { exact: 1.0, lookalike: 0.7, unknown: 1.0 },
    timing_conf: {
      typical: 1.0,
      in_range: 0.7,
      fast: 0.5,
      slow_near: 0.6,
      slow_far: 0.4,
      unlinked: 0.4,
    },
    appearance: { enabled: false },
  };

  const sampleLinks: CameraLink[] = [
    { a: 'CAM-01', b: 'CAM-02', min_s: 240, typical_s: 360, max_s: 600, direction: 'both', overlap: false },
    { a: 'CAM-02', b: 'CAM-03', min_s: 90, typical_s: 150, max_s: 300, direction: 'both', overlap: false },
    { a: 'CAM-03', b: 'CAM-04', min_s: 15, typical_s: 30, max_s: 90, direction: 'both', overlap: false },
    { a: 'CAM-02', b: 'CAM-04', min_s: 300, typical_s: 420, max_s: 720, direction: 'both', overlap: false },
    { a: 'CAM-04', b: 'CAM-05', min_s: 40, typical_s: 70, max_s: 180, direction: 'both', overlap: false },
  ];

  const topo = new TopologyIndex(sampleLinks);

  function sighting(
    camera_id: string,
    firstIso: string,
    lastIso: string = firstIso,
    event_ids: string[] = [`evt-${camera_id}`],
    plates: string[] = ['KA01AB1234']
  ): Sighting {
    return {
      camera_id,
      first_seen: firstIso,
      last_seen: lastIso,
      event_count: 1,
      max_score: 90,
      event_types: ['PLATE_ALERT'],
      event_ids,
      plates,
      plate_quality: 'exact',
    };
  }

  it('Plan Scenario 3: 3 sightings -> 1 trip, 1 trajectory, PLAUSIBLE links at 100%, no anomalies', () => {
    const sightings = [
      sighting('CAM-01', '2026-11-01T10:02:00.000000Z', '2026-11-01T10:02:00.000000Z'),
      sighting('CAM-02', '2026-11-01T10:08:00.000000Z', '2026-11-01T10:08:00.000000Z'), // +360 s
      sighting('CAM-04', '2026-11-01T10:15:00.000000Z', '2026-11-01T10:15:00.000000Z'), // +420 s
    ];

    const result = correlate(sightings, topo, cfg);
    expect(result.trips).toHaveLength(1);
    expect(result.anomalies).toHaveLength(0);

    const trip = result.trips[0]!;
    expect(trip.trajectories).toHaveLength(1);
    const traj = trip.trajectories[0]!;
    expect(traj.cameras).toEqual(['CAM-01', 'CAM-02', 'CAM-04']);
    expect(traj.links).toHaveLength(2);
    expect(traj.links[0]!.class).toBe('PLAUSIBLE');
    expect(traj.links[0]!.gap_s).toBe(360);
    expect(traj.links[1]!.class).toBe('PLAUSIBLE');
    expect(traj.links[1]!.gap_s).toBe(420);
    expect(traj.confidence).toBe(1.0);
  });

  it('Day 18 example: gaps 28 s and 72 s, PLAUSIBLE, no anomalies', () => {
    const sightings = [
      sighting('CAM-03', '2026-11-01T02:13:42.000000Z'),
      sighting('CAM-04', '2026-11-01T02:14:10.000000Z'), // +28 s
      sighting('CAM-05', '2026-11-01T02:15:22.000000Z'), // +72 s
    ];

    const result = correlate(sightings, topo, cfg);
    expect(result.trips).toHaveLength(1);
    expect(result.anomalies).toHaveLength(0);
    const traj = result.trips[0]!.trajectories[0]!;
    expect(traj.cameras).toEqual(['CAM-03', 'CAM-04', 'CAM-05']);
    expect(traj.links[0]!.gap_s).toBe(28);
    expect(traj.links[1]!.gap_s).toBe(72);
  });

  it('detects impossible travel and multiple trajectories on duplicate plate scenario', () => {
    // KA01AB1234 CAM-01 10:02:00
    // KA01AB1234 CAM-04 10:03:00 (60s later; fastest route >= 345s)
    // KA01AB1234 CAM-02 10:08:00 (plausible after CAM-01: 360s)
    // KA01AB1234 CAM-05 10:04:10 (plausible after CAM-04: 70s)
    const sightings = [
      sighting('CAM-01', '2026-11-01T10:02:00.000000Z'),
      sighting('CAM-04', '2026-11-01T10:03:00.000000Z'),
      sighting('CAM-05', '2026-11-01T10:04:10.000000Z'),
      sighting('CAM-02', '2026-11-01T10:08:00.000000Z'),
    ];

    const result = correlate(sightings, topo, cfg);
    expect(result.trips).toHaveLength(1);
    const trip = result.trips[0]!;
    expect(trip.trajectories).toHaveLength(2);

    const t1 = trip.trajectories.find(t => t.cameras[0] === 'CAM-01');
    const t2 = trip.trajectories.find(t => t.cameras[0] === 'CAM-04');
    expect(t1?.cameras).toEqual(['CAM-01', 'CAM-02']);
    expect(t2?.cameras).toEqual(['CAM-04', 'CAM-05']);

    const types = result.anomalies.map(a => a.type);
    expect(types).toContain('IMPOSSIBLE_TRAVEL');
    expect(types).toContain('MULTIPLE_TRAJECTORIES');

    const imp = result.anomalies.find(a => a.type === 'IMPOSSIBLE_TRAVEL')!;
    expect(imp.message).toContain('60 s');
    expect(imp.message).toContain('CAM-04');
  });

  it('detects simultaneous sightings on two non-overlapping cameras', () => {
    const sightings = [
      sighting('CAM-01', '2026-11-01T10:00:00.000000Z', '2026-11-01T10:00:10.000000Z'),
      sighting('CAM-05', '2026-11-01T10:00:08.000000Z', '2026-11-01T10:00:15.000000Z'), // starts before CAM-01 leaves
    ];

    const result = correlate(sightings, topo, cfg);
    const types = result.anomalies.map(a => a.type);
    expect(types).toContain('SIMULTANEOUS_SIGHTINGS');
    expect(types).toContain('MULTIPLE_TRAJECTORIES');
  });

  it('flags MISSED_CAMERA when only route via CAM-03 fits', () => {
    const sightings = [
      sighting('CAM-02', '2026-11-01T10:00:00.000000Z'),
      sighting('CAM-04', '2026-11-01T10:02:58.000000Z'), // +178 s
    ];

    const result = correlate(sightings, topo, cfg);
    const missed = result.anomalies.find(a => a.type === 'MISSED_CAMERA');
    expect(missed).toBeDefined();
    expect(missed?.evidence['missed_cameras']).toEqual(['CAM-03']);
  });

  it('segments into multiple trips when gap exceeds trip_break_s', () => {
    const sightings8h = [
      sighting('CAM-01', '2026-11-01T10:00:00.000000Z'),
      sighting('CAM-02', '2026-11-01T18:00:00.000000Z'), // 8 hours later
    ];
    const res8h = correlate(sightings8h, topo, cfg);
    expect(res8h.trips).toHaveLength(2);

    const sightings5h59m = [
      sighting('CAM-01', '2026-11-01T10:00:00.000000Z'),
      sighting('CAM-02', '2026-11-01T15:59:00.000000Z'), // 5h 59m later (21540s <= 21600s)
    ];
    const res5h59m = correlate(sightings5h59m, topo, cfg);
    expect(res5h59m.trips).toHaveLength(1);
  });

  it('triggers TRAJECTORY_OVERFLOW when exceeding max_trajectories', () => {
    // 5 sightings simultaneously across different cameras
    const sightings = [
      sighting('CAM-01', '2026-11-01T10:00:00.000000Z', '2026-11-01T10:00:10.000000Z', ['e1']),
      sighting('CAM-02', '2026-11-01T10:00:01.000000Z', '2026-11-01T10:00:10.000000Z', ['e2']),
      sighting('CAM-03', '2026-11-01T10:00:02.000000Z', '2026-11-01T10:00:10.000000Z', ['e3']),
      sighting('CAM-04', '2026-11-01T10:00:03.000000Z', '2026-11-01T10:00:10.000000Z', ['e4']),
      sighting('CAM-05', '2026-11-01T10:00:04.000000Z', '2026-11-01T10:00:10.000000Z', ['e5']),
    ];

    const result = correlate(sightings, topo, { ...cfg, max_trajectories: 4 });
    const overflow = result.anomalies.find(a => a.type === 'TRAJECTORY_OVERFLOW');
    expect(overflow).toBeDefined();
    expect(result.trips[0]!.trajectories.length).toBeLessThanOrEqual(4);
  });

  it('deterministically breaks ties on equal first_seen values', () => {
    const sA = sighting('CAM-01', '2026-11-01T10:00:00.000000Z', '2026-11-01T10:00:00.000000Z', ['evt-A']);
    const sB = sighting('CAM-02', '2026-11-01T10:00:00.000000Z', '2026-11-01T10:00:00.000000Z', ['evt-B']);

    const res1 = correlate([sA, sB], topo, cfg);
    const res2 = correlate([sB, sA], topo, cfg);
    expect(JSON.stringify(res1)).toBe(JSON.stringify(res2));
  });

  it('guarantees shuffled-input determinism across 100 random permutations', () => {
    const sightings = [
      sighting('CAM-01', '2026-11-01T10:02:00.000000Z', '2026-11-01T10:02:00.000000Z', ['e1']),
      sighting('CAM-04', '2026-11-01T10:03:00.000000Z', '2026-11-01T10:03:00.000000Z', ['e2']),
      sighting('CAM-05', '2026-11-01T10:04:10.000000Z', '2026-11-01T10:04:10.000000Z', ['e3']),
      sighting('CAM-02', '2026-11-01T10:08:00.000000Z', '2026-11-01T10:08:00.000000Z', ['e4']),
      sighting('CAM-04', '2026-11-01T10:15:00.000000Z', '2026-11-01T10:15:00.000000Z', ['e5']),
      sighting('CAM-05', '2026-11-01T10:16:15.000000Z', '2026-11-01T10:16:15.000000Z', ['e6']),
    ];

    const baselineJson = JSON.stringify(correlate(sightings, topo, cfg));

    for (let i = 0; i < 100; i++) {
      const shuffled = [...sightings].sort(() => Math.random() - 0.5);
      const outputJson = JSON.stringify(correlate(shuffled, topo, cfg));
      expect(outputJson).toBe(baselineJson);
    }
  });

  it('does not mutate input array or input sighting objects', () => {
    const s1 = Object.freeze(sighting('CAM-01', '2026-11-01T10:02:00.000000Z'));
    const s2 = Object.freeze(sighting('CAM-02', '2026-11-01T10:08:00.000000Z'));
    const arr = Object.freeze([s2, s1]);

    expect(() => correlate(arr as unknown as Sighting[], topo, cfg)).not.toThrow();
  });
});
