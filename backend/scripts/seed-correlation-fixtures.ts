import fs from 'node:fs';
import path from 'node:path';
import type { EventRow } from '../src/modules/events/repo.js';

export interface CorrelationFixtureData {
  events: EventRow[];
  metadata: {
    generated_at: string;
    total_events: number;
    scenario_counts: Record<string, number>;
  };
}

export function generateCorrelationFixtures(): CorrelationFixtureData {
  const events: EventRow[] = [];
  const counts: Record<string, number> = {};

  const addEvt = (
    id: string,
    cam: string,
    iso: string,
    plate: string | null,
    vehicle_id: string | null = null,
    score = 40
  ) => {
    events.push({
      event_id: id,
      camera_id: cam,
      event_type: 'ANPR_MATCH',
      track_id: id,
      severity: 'LOW',
      threat_score: score,
      timestamp: iso,
      snapshot_path: null,
      plate,
      vehicle_id,
      metadata: { synthetic: true },
    });
  };

  // 1. Plan Scenario 3 (1 plate: KA01AB1234)
  // CAM-01 10:02 -> CAM-02 10:08 -> CAM-04 10:15
  addEvt('sc3-1', 'CAM-01', '2026-11-01T10:02:00.000000Z', 'KA01AB1234');
  addEvt('sc3-2', 'CAM-02', '2026-11-01T10:08:00.000000Z', 'KA01AB1234');
  addEvt('sc3-3', 'CAM-04', '2026-11-01T10:15:00.000000Z', 'KA01AB1234');
  counts['scenario_3'] = 1;

  // 2. Day 18 example (1 plate: MH12DE3344)
  // 02:13:42 CAM-03 -> 02:14:10 CAM-04 -> 02:15:22 CAM-05
  addEvt('d18-1', 'CAM-03', '2026-11-01T02:13:42.000000Z', 'MH12DE3344');
  addEvt('d18-2', 'CAM-04', '2026-11-01T02:14:10.000000Z', 'MH12DE3344');
  addEvt('d18-3', 'CAM-05', '2026-11-01T02:15:22.000000Z', 'MH12DE3344');
  counts['day_18_example'] = 1;

  // 3. Impossible travel / duplicated plate (5 plates: DUP-01 to DUP-05)
  // CAM-01 at 10:02, CAM-04 at 10:03 (60s gap, fastest min_s = 345s)
  for (let i = 1; i <= 5; i++) {
    const p = `DUP0${i}AA1111`;
    addEvt(`dup-${i}-1`, 'CAM-01', '2026-11-01T10:02:00.000000Z', p);
    addEvt(`dup-${i}-2`, 'CAM-04', '2026-11-01T10:03:00.000000Z', p);
  }
  counts['impossible_travel'] = 5;

  // 4. Missing middle camera (5 plates: MIS-01 to MIS-05)
  // CAM-02 -> CAM-04 in 178 s (only route via CAM-03 fits -> missed CAM-03)
  for (let i = 1; i <= 5; i++) {
    const p = `MIS0${i}BB2222`;
    addEvt(`mis-${i}-1`, 'CAM-02', '2026-11-01T11:00:00.000000Z', p);
    addEvt(`mis-${i}-2`, 'CAM-04', '2026-11-01T11:02:58.000000Z', p);
  }
  counts['missing_middle'] = 5;

  // 5. Look-alike variants (3 plates: LOOK-01 to LOOK-03)
  for (let i = 1; i <= 3; i++) {
    const pExact = `LOOK0${i}AB1234`;
    const pLookalike = `LOOK0${i}ABI234`;
    addEvt(`look-${i}-1`, 'CAM-01', '2026-11-01T12:00:00.000000Z', pExact);
    addEvt(`look-${i}-2`, 'CAM-02', '2026-11-01T12:06:00.000000Z', pLookalike);
  }
  counts['lookalike_variants'] = 3;

  // 6. Slow transit (2 plates: SLOW-01 to SLOW-02)
  // CAM-01 -> CAM-02 after 40 min (2400 s)
  for (let i = 1; i <= 2; i++) {
    const p = `SLOW0${i}CC3333`;
    addEvt(`slow-${i}-1`, 'CAM-01', '2026-11-01T13:00:00.000000Z', p);
    addEvt(`slow-${i}-2`, 'CAM-02', '2026-11-01T13:40:00.000000Z', p);
  }
  counts['slow_transit'] = 2;

  // 7. Trip break (2 plates: TRIP-01 to TRIP-02)
  // same route twice, 9 h apart (gap 32400s > 21600s)
  for (let i = 1; i <= 2; i++) {
    const p = `TRIP0${i}DD4444`;
    addEvt(`trip-${i}-1`, 'CAM-01', '2026-11-01T08:00:00.000000Z', p);
    addEvt(`trip-${i}-2`, 'CAM-02', '2026-11-01T08:06:00.000000Z', p);
    addEvt(`trip-${i}-3`, 'CAM-01', '2026-11-01T17:06:00.000000Z', p);
    addEvt(`trip-${i}-4`, 'CAM-02', '2026-11-01T17:12:00.000000Z', p);
  }
  counts['trip_break'] = 2;

  // 8. Near-miss decoy (KA01AB1235)
  // CAM-04 02:14:11 (decoy for KA01AB1234, different plate_key)
  addEvt('decoy-1', 'CAM-04', '2026-11-01T02:14:11.000000Z', 'KA01AB1235');
  counts['near_miss_decoy'] = 1;

  // 9. Normal routes (20 plates: NORM-01 to NORM-20)
  // Random valid routes with gaps sampled inside min-max
  for (let i = 1; i <= 20; i++) {
    const p = `NORM${String(i).padStart(2, '0')}EE5555`;
    const baseMin = 14 * 60 + i * 10;
    const t0 = new Date(Date.UTC(2026, 10, 1, Math.floor(baseMin / 60), baseMin % 60, 0));
    const t1 = new Date(t0.getTime() + 360 * 1000);
    const t2 = new Date(t1.getTime() + 420 * 1000);

    addEvt(`norm-${i}-1`, 'CAM-01', t0.toISOString(), p);
    addEvt(`norm-${i}-2`, 'CAM-02', t1.toISOString(), p);
    addEvt(`norm-${i}-3`, 'CAM-04', t2.toISOString(), p);
  }
  counts['normal_routes'] = 20;

  return {
    events,
    metadata: {
      generated_at: new Date().toISOString(),
      total_events: events.length,
      scenario_counts: counts,
    },
  };
}

export function writeFixtures(outPath?: string): void {
  const rootDir = fs.existsSync(path.resolve(process.cwd(), 'configs'))
    ? process.cwd()
    : path.resolve(process.cwd(), '..');
  const p = outPath ?? path.resolve(rootDir, 'docs/fixtures/correlation_fixtures.json');
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const data = generateCorrelationFixtures();
  fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf-8');
  console.log(`[seed-correlation-fixtures] Written ${data.events.length} fixture events to ${p}`);
}

if (process.argv[1]?.includes('seed-correlation-fixtures')) {
  writeFixtures();
}
