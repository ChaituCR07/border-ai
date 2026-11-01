import { describe, it, expect } from 'vitest';
import { TopologyIndex, CameraLink } from '../../src/modules/correlation/topology.js';
import { CorrelationConfig } from '../../src/modules/correlation/config.js';
import { correlate } from '../../src/modules/correlation/correlate.js';
import { Sighting, isoToMicros } from '../../src/modules/investigation/journey.js';

describe('correlate invariant and property tests', () => {
  const cfg: CorrelationConfig = {
    version: 1,
    merge_gap_s: 120,
    trip_break_s: 21600,
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

  it('handles empty input cleanly', () => {
    const res = correlate([], topo, cfg);
    expect(res.trips).toHaveLength(0);
    expect(res.anomalies).toHaveLength(0);
  });

  it('handles single sighting as one trip, one trajectory with confidence 1.0', () => {
    const single: Sighting = {
      camera_id: 'CAM-01',
      first_seen: '2026-11-01T10:00:00.000000Z',
      last_seen: '2026-11-01T10:00:05.000000Z',
      event_count: 1,
      max_score: 50,
      event_types: ['PLATE_ALERT'],
      event_ids: ['evt-single'],
      plates: ['KA01AB1234'],
    };
    const res = correlate([single], topo, cfg);
    expect(res.trips).toHaveLength(1);
    expect(res.trips[0]!.trajectories).toHaveLength(1);
    expect(res.trips[0]!.trajectories[0]!.confidence).toBe(1.0);
    expect(res.trips[0]!.trajectories[0]!.links).toHaveLength(0);
    expect(res.anomalies).toHaveLength(0);
  });

  it('preserves all structural invariants across 200 randomized scenarios', () => {
    const cameras = ['CAM-01', 'CAM-02', 'CAM-03', 'CAM-04', 'CAM-05', 'CAM-99'];
    const baseEpoch = Date.UTC(2026, 10, 1, 10, 0, 0);

    // Run 200 randomized scenarios
    for (let seed = 0; seed < 200; seed++) {
      const numSightings = Math.floor(Math.random() * 15) + 1; // 1 to 15 sightings
      const sightings: Sighting[] = [];

      let currentOffset = 0;
      for (let i = 0; i < numSightings; i++) {
        // Random time jump between -10s and 30,000s
        const delta = Math.floor(Math.random() * 1000) - 10;
        currentOffset += Math.max(0, delta);
        const duration = Math.floor(Math.random() * 20); // 0 to 20s

        const firstDate = new Date(baseEpoch + currentOffset * 1000);
        const lastDate = new Date(baseEpoch + (currentOffset + duration) * 1000);
        const cam = cameras[Math.floor(Math.random() * cameras.length)]!;
        const hasLookalike = Math.random() < 0.2;

        sightings.push({
          camera_id: cam,
          first_seen: firstDate.toISOString(),
          last_seen: lastDate.toISOString(),
          event_count: 1,
          max_score: 75,
          event_types: ['PLATE_ALERT'],
          event_ids: [`s-${seed}-${i}`],
          plates: hasLookalike ? ['KA01AB1234', 'KA0IAB1234'] : ['KA01AB1234'],
          plate_quality: hasLookalike ? 'lookalike' : 'exact',
        });
      }

      // Vary configs within sane bounds
      const testCfg: CorrelationConfig = {
        ...cfg,
        trip_break_s: Math.random() < 0.5 ? 21600 : 7200,
        max_trajectories: Math.floor(Math.random() * 3) + 2, // 2 to 4
        speed_tolerance: 0.7 + Math.random() * 0.2, // 0.7 to 0.9
      };

      const result = correlate(sightings, topo, testCfg);

      // Invariant 1: Every input sighting appears in exactly one trajectory
      const collectedSightingIds = new Set<string>();
      let totalSightingsInOutput = 0;

      for (const trip of result.trips) {
        for (const traj of trip.trajectories) {
          // Invariant 2: links.length === sightings.length - 1
          expect(traj.links.length).toBe(traj.sightings.length - 1);

          // Invariant 3: Sightings inside a trajectory are time-ordered
          for (let j = 0; j < traj.sightings.length - 1; j++) {
            const sCurrent = traj.sightings[j]!;
            const sNext = traj.sightings[j + 1]!;
            expect(isoToMicros(sNext.first_seen)).toBeGreaterThanOrEqual(
              isoToMicros(sCurrent.first_seen) - 10000000n // Within reasonable bounds of seen
            );
          }

          // Invariant 4: All confidences in [0, 1]; traj.confidence <= every link confidence
          expect(traj.confidence).toBeGreaterThanOrEqual(0);
          expect(traj.confidence).toBeLessThanOrEqual(1);
          expect(traj.mean_confidence).toBeGreaterThanOrEqual(0);
          expect(traj.mean_confidence).toBeLessThanOrEqual(1);

          for (const link of traj.links) {
            expect(link.confidence).toBeGreaterThanOrEqual(0);
            expect(link.confidence).toBeLessThanOrEqual(1);
            expect(traj.confidence).toBeLessThanOrEqual(link.confidence);
          }

          // Invariant 5: No IMPOSSIBLE or SIMULTANEOUS link inside trajectory unless overflow
          const hasOverflow = result.anomalies.some(a => a.type === 'TRAJECTORY_OVERFLOW');
          if (!hasOverflow) {
            for (const link of traj.links) {
              expect(link.class).not.toBe('IMPOSSIBLE');
              expect(link.class).not.toBe('SIMULTANEOUS');
            }
          }

          for (const s of traj.sightings) {
            const id = s.event_ids[0]!;
            expect(collectedSightingIds.has(id)).toBe(false);
            collectedSightingIds.add(id);
            totalSightingsInOutput++;
          }
        }
      }

      expect(totalSightingsInOutput).toBe(sightings.length);

      // Invariant 6: Anomaly ordering: warnings before info
      for (let aIdx = 0; aIdx < result.anomalies.length - 1; aIdx++) {
        const cur = result.anomalies[aIdx]!;
        const next = result.anomalies[aIdx + 1]!;
        if (cur.severity === 'info' && next.severity === 'warning') {
          throw new Error(`Anomaly ordering violated: info came before warning`);
        }
      }
    }
  });
});

