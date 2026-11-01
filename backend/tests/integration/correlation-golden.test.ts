import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import fs from 'node:fs';
import path from 'node:path';
import { createTestApp } from '../helpers/test-app.js';
import type { InMemoryInvestigationRepo } from '../../src/modules/investigation/repo.memory.js';
import { generateCorrelationFixtures } from '../../scripts/seed-correlation-fixtures.js';
import { TopologyIndex, CameraLink } from '../../src/modules/correlation/topology.js';
import { correlate } from '../../src/modules/correlation/correlate.js';
import { loadCorrelationConfig } from '../../src/modules/correlation/config.js';
import { Sighting } from '../../src/modules/investigation/journey.js';

describe('Correlation Golden Integration & Performance Tests', () => {
  let app: FastifyInstance;
  let repo: InMemoryInvestigationRepo;
  let expected: any;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
    repo = res.investigationRepo;

    const fixtureData = generateCorrelationFixtures();
    await repo.seed(fixtureData.events);

    // Read docs/fixtures/correlation_expected.json
    const expectedPath = path.resolve(process.cwd(), 'docs/fixtures/correlation_expected.json');
    const fallbackPath = path.resolve(process.cwd(), '../docs/fixtures/correlation_expected.json');
    const p = fs.existsSync(expectedPath) ? expectedPath : fallbackPath;
    expected = JSON.parse(fs.readFileSync(p, 'utf-8')).scenarios;
  });

  describe('Scenario verification against expected fixtures', () => {
    it('verifies Plan Scenario 3 (KA01AB1234)', async () => {
      const exp = expected.scenario_3;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      expect(data.correlation.trips).toHaveLength(exp.trips_count);
      const trip = data.correlation.trips[0];
      expect(trip.trajectories).toHaveLength(exp.trajectories_count);
      const traj = trip.trajectories[0];
      expect(traj.cameras).toEqual(exp.cameras);
      expect(traj.links).toHaveLength(exp.links_count);
      expect(traj.links.map((l: any) => l.class)).toEqual(exp.link_classes);
      expect(traj.confidence).toBe(exp.confidence);
      expect(data.correlation.anomalies).toHaveLength(exp.anomalies_count);
    });

    it('verifies Day 18 example (MH12DE3344)', async () => {
      const exp = expected.day_18_example;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      expect(data.correlation.trips).toHaveLength(exp.trips_count);
      const traj = data.correlation.trips[0].trajectories[0];
      expect(traj.cameras).toEqual(exp.cameras);
      expect(traj.links.map((l: any) => l.class)).toEqual(exp.link_classes);
      expect(traj.links.map((l: any) => l.gap_s)).toEqual(exp.gaps_s);
      expect(data.correlation.anomalies).toHaveLength(exp.anomalies_count);
    });

    it('verifies Impossible Travel (DUP01AA1111)', async () => {
      const exp = expected.impossible_travel;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.sample_plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      expect(data.correlation.trips).toHaveLength(exp.trips_count);
      expect(data.correlation.trips[0].trajectories).toHaveLength(exp.trajectories_count);

      const anomalyTypes = data.correlation.anomalies.map((a: any) => a.type);
      for (const t of exp.anomaly_types) {
        expect(anomalyTypes).toContain(t);
      }
    });

    it('verifies Missing Middle Camera (MIS01BB2222)', async () => {
      const exp = expected.missing_middle;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.sample_plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      const missed = data.correlation.anomalies.find((a: any) => a.type === 'MISSED_CAMERA');
      expect(missed).toBeDefined();
      expect(missed.evidence.missed_cameras).toEqual(exp.missed_cameras);
    });

    it('verifies Look-alike variants (LOOK01AB1234)', async () => {
      const exp = expected.lookalike_variants;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.sample_plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      const traj = data.correlation.trips[0].trajectories[0];
      expect(traj.links[0].confidence).toBe(exp.confidence);
      const plateFactor = traj.links[0].factors.find((f: any) => f.name === 'plate');
      expect(plateFactor.value).toBe(exp.plate_factor);
    });

    it('verifies Slow Transit (SLOW01CC3333)', async () => {
      const exp = expected.slow_transit;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.sample_plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      const traj = data.correlation.trips[0].trajectories[0];
      expect(traj.links[0].class).toBe('SLOW');
      const slow = data.correlation.anomalies.find((a: any) => a.type === 'SLOW_TRANSIT');
      expect(slow).toBeDefined();
    });

    it('verifies Trip Break (TRIP01DD4444)', async () => {
      const exp = expected.trip_break;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.sample_plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      expect(data.correlation.trips).toHaveLength(exp.trips_count);
    });

    it('verifies Near-miss decoy does not correlate into target journey', async () => {
      const exp = expected.near_miss_decoy;
      const res = await app.inject({
        method: 'GET',
        url: `/api/investigation/journey?plate=${exp.target_plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
        headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
      });

      expect(res.statusCode).toBe(200);
      const { data } = res.json();
      for (const sighting of data.sightings) {
        expect(sighting.plates).not.toContain(exp.plate);
      }
    });

    it('verifies 20 Normal Routes have 0 warnings', async () => {
      for (let i = 1; i <= 20; i++) {
        const plate = `NORM${String(i).padStart(2, '0')}EE5555`;
        const res = await app.inject({
          method: 'GET',
          url: `/api/investigation/journey?plate=${plate}&from=2026-11-01T00:00:00.000Z&to=2026-11-01T23:59:59.000Z`,
          headers: { 'x-actor-role': 'OPERATOR', 'x-actor-id': 'op-1' },
        });

        expect(res.statusCode).toBe(200);
        const { data } = res.json();
        const warnings = data.correlation.anomalies.filter((a: any) => a.severity === 'warning');
        expect(warnings).toHaveLength(0);
      }
    });
  });

  describe('Performance targets', () => {
    it('TopologyIndex build with 50 cameras / 80 links finishes in < 200 ms', () => {
      const links: CameraLink[] = [];
      for (let i = 1; i <= 50; i++) {
        const next = i < 50 ? i + 1 : 1;
        const cross = ((i * 7) % 50) + 1;
        links.push({
          a: `C${i}`,
          b: `C${next}`,
          min_s: 30,
          typical_s: 60,
          max_s: 120,
          direction: 'both',
        });
        if (i % 2 === 0 && cross !== i) {
          links.push({
            a: `C${i}`,
            b: `C${cross}`,
            min_s: 50,
            typical_s: 100,
            max_s: 200,
            direction: 'both',
          });
        }
      }

      const start = performance.now();
      const topo = new TopologyIndex(links.slice(0, 80), { maxHops: 4, maxRoutesPerPair: 20 });
      const elapsed = performance.now() - start;

      expect(topo.version).toBeDefined();
      expect(elapsed).toBeLessThan(200);
    });

    it('7x7 grid completes with route cap enforced in < 1000 ms', () => {
      const gridLinks: CameraLink[] = [];
      for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 7; c++) {
          const id = `G_${r}_${c}`;
          if (c + 1 < 7) {
            gridLinks.push({ a: id, b: `G_${r}_${c + 1}`, min_s: 10, typical_s: 20, max_s: 40 });
          }
          if (r + 1 < 7) {
            gridLinks.push({ a: id, b: `G_${r + 1}_${c}`, min_s: 10, typical_s: 20, max_s: 40 });
          }
        }
      }

      const start = performance.now();
      const topo = new TopologyIndex(gridLinks, { maxHops: 4, maxRoutesPerPair: 20 });
      const elapsed = performance.now() - start;

      expect(topo.version).toBeDefined();
      expect(elapsed).toBeLessThan(1000);
    });

    it('correlate() with 500 sightings finishes in < 50 ms', () => {
      const cfg = loadCorrelationConfig();
      const sampleLinks: CameraLink[] = [
        { a: 'CAM-01', b: 'CAM-02', min_s: 240, typical_s: 360, max_s: 600, direction: 'both' },
        { a: 'CAM-02', b: 'CAM-03', min_s: 90, typical_s: 150, max_s: 300, direction: 'both' },
        { a: 'CAM-03', b: 'CAM-04', min_s: 15, typical_s: 30, max_s: 90, direction: 'both' },
        { a: 'CAM-02', b: 'CAM-04', min_s: 300, typical_s: 420, max_s: 720, direction: 'both' },
        { a: 'CAM-04', b: 'CAM-05', min_s: 40, typical_s: 70, max_s: 180, direction: 'both' },
      ];
      const topo = new TopologyIndex(sampleLinks);

      const sightings: Sighting[] = [];
      const base = Date.UTC(2026, 10, 1, 10, 0, 0);
      const cams = ['CAM-01', 'CAM-02', 'CAM-04', 'CAM-05'];

      for (let i = 0; i < 500; i++) {
        const cam = cams[i % cams.length]!;
        const t = new Date(base + i * 360 * 1000).toISOString();
        sightings.push({
          camera_id: cam,
          first_seen: t,
          last_seen: t,
          event_count: 1,
          max_score: 50,
          event_types: ['ANPR_MATCH'],
          event_ids: [`perf-${i}`],
          plates: ['PERF01AA1111'],
        });
      }

      const start = performance.now();
      const res = correlate(sightings, topo, cfg);
      const elapsed = performance.now() - start;

      expect(res.trips.length).toBeGreaterThan(0);
      expect(elapsed).toBeLessThan(50);
    });
  });
});
