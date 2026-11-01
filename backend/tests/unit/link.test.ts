import { describe, it, expect } from 'vitest';
import { TopologyIndex, CameraLink } from '../../src/modules/correlation/topology.js';
import { evaluateLink, fmt, closest, round3 } from '../../src/modules/correlation/link.js';
import { CorrelationConfig } from '../../src/modules/correlation/config.js';
import { Sighting } from '../../src/modules/investigation/journey.js';

describe('link evaluation and helpers', () => {
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
    { a: 'CAM-OV1', b: 'CAM-OV2', min_s: 0, typical_s: 10, max_s: 30, direction: 'both', overlap: true },
  ];

  const topo = new TopologyIndex(sampleLinks);

  function makeSighting(
    camera_id: string,
    firstIso: string,
    lastIso: string,
    plates: string[] = ['MH12AB1234'],
    plate_quality?: 'exact' | 'lookalike' | 'unknown'
  ): Sighting {
    return {
      camera_id,
      first_seen: firstIso,
      last_seen: lastIso,
      event_count: 1,
      max_score: 80,
      event_types: ['PLATE_ALERT'],
      event_ids: ['evt-1'],
      plates,
      plate_quality,
    };
  }

  describe('helper functions', () => {
    it('formats seconds into readable strings (fmt)', () => {
      expect(fmt(28)).toBe('28 s');
      expect(fmt(360)).toBe('6 min');
      expect(fmt(65)).toBe('1 min 5 s');
      expect(fmt(3900)).toBe('1 h 05 min');
    });

    it('finds closest route with tie-breaking rules', () => {
      const routes = topo.routesBetween('CAM-02', 'CAM-04');
      // CAM-02 -> CAM-04 has direct (typical 420, 2 cameras) and via CAM-03 (typical 180, 3 cameras)
      expect(closest(routes, 400).cameras).toEqual(['CAM-02', 'CAM-04']);
      expect(closest(routes, 170).cameras).toEqual(['CAM-02', 'CAM-03', 'CAM-04']);
    });
  });

  describe('boundary table verification', () => {
    const baseDate = '2026-11-01T10:00:00.000000Z';

    const sightingAt = (
      cam: string,
      offsetS: number,
      durationS: number = 0,
      plates?: string[],
      quality?: 'exact' | 'lookalike' | 'unknown'
    ) => {
      const start = new Date(new Date(baseDate).getTime() + offsetS * 1000).toISOString();
      const end = new Date(new Date(baseDate).getTime() + (offsetS + durationS) * 1000).toISOString();
      return makeSighting(cam, start, end, plates, quality);
    };

    it('CAM-01 -> CAM-02, 360 s: PLAUSIBLE, confidence 1.0 (typical)', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-02', 360);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(1.0);
    });

    it('CAM-01 -> CAM-02, 240 s: PLAUSIBLE, confidence 0.7 (min, outside typical band)', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-02', 240);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(0.7);
    });

    it('CAM-01 -> CAM-02, 200 s: FAST, confidence 0.5 (>= 0.8 * 240 = 192)', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-02', 200);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('FAST');
      expect(link.confidence).toBe(0.5);
    });

    it('CAM-01 -> CAM-02, 190 s: IMPOSSIBLE, confidence 0.0 (< 192)', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-02', 190);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('IMPOSSIBLE');
      expect(link.confidence).toBe(0.0);
    });

    it('CAM-01 -> CAM-02, 700 s: SLOW, confidence 0.6 (> 600, <= 3 * 600)', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-02', 700);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('SLOW');
      expect(link.confidence).toBe(0.6);
    });

    it('CAM-02 -> CAM-04, 420 s: PLAUSIBLE, confidence 1.0 (direct, no missed cameras)', () => {
      const a = sightingAt('CAM-02', 0);
      const b = sightingAt('CAM-04', 420);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(1.0);
      expect(link.missed_cameras).toEqual([]);
    });

    it('CAM-02 -> CAM-04, 178 s: PLAUSIBLE, confidence 1.0, missed_cameras: [CAM-03]', () => {
      const a = sightingAt('CAM-02', 0);
      const b = sightingAt('CAM-04', 178);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(1.0);
      expect(link.missed_cameras).toEqual(['CAM-03']);
    });

    it('CAM-01 -> CAM-04, 60 s: IMPOSSIBLE, confidence 0.0 (fastest route min 345s)', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-04', 60);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('IMPOSSIBLE');
      expect(link.confidence).toBe(0.0);
    });

    it('CAM-03 -> CAM-04, 28 s: PLAUSIBLE, confidence 1.0', () => {
      const a = sightingAt('CAM-03', 0);
      const b = sightingAt('CAM-04', 28);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(1.0);
    });

    it('CAM-04 -> CAM-05, 72 s: PLAUSIBLE, confidence 1.0', () => {
      const a = sightingAt('CAM-04', 0);
      const b = sightingAt('CAM-05', 72);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(1.0);
    });

    it('CAM-01 -> CAM-05, -2 s: SIMULTANEOUS, confidence 0.0 (no overlap)', () => {
      const a = sightingAt('CAM-01', 10, 5); // 10..15
      const b = sightingAt('CAM-05', 13); // starts at 13, gap = 13 - 15 = -2s
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('SIMULTANEOUS');
      expect(link.confidence).toBe(0.0);
    });

    it('CAM-01 -> CAM-99, 100 s: UNLINKED, confidence 0.4', () => {
      const a = sightingAt('CAM-01', 0);
      const b = sightingAt('CAM-99', 100);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('UNLINKED');
      expect(link.confidence).toBe(0.4);
    });

    it('look-alike plate scales confidence by 0.7', () => {
      const a = sightingAt('CAM-01', 0, 0, ['KA01AB1234'], 'exact');
      const b = sightingAt('CAM-02', 360, 0, ['KA0IAB1234'], 'lookalike');
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('PLAUSIBLE');
      expect(link.confidence).toBe(0.7);
      expect(link.factors[0].name).toBe('plate');
      expect(link.factors[0].value).toBe(0.7);
    });

    it('same camera revisit returns REVISIT with 1.0', () => {
      const a = sightingAt('CAM-01', 0, 5);
      const b = sightingAt('CAM-01', 60);
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('REVISIT');
      expect(link.confidence).toBe(1.0);
    });

    it('overlapping cameras with small negative gap return OVERLAP_OK', () => {
      const a = sightingAt('CAM-OV1', 0, 10); // 0..10
      const b = sightingAt('CAM-OV2', 7); // gap = 7 - 10 = -3s >= -5s tolerance
      const link = evaluateLink(a, b, topo, cfg);
      expect(link.class).toBe('OVERLAP_OK');
      expect(link.confidence).toBe(1.0);
    });
  });
});

