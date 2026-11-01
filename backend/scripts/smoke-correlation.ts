import { loadTopologyConfig } from './topology-check.js';
import { loadCorrelationConfig } from '../src/modules/correlation/config.js';
import { TopologyIndex } from '../src/modules/correlation/topology.js';
import { evaluateLink } from '../src/modules/correlation/link.js';
import { correlate } from '../src/modules/correlation/correlate.js';
import { parseCameraSequence, verifySequenceHops } from '../src/modules/correlation/sequence.js';
import { Sighting } from '../src/modules/investigation/journey.js';

async function runCorrelationSmoke() {
  console.log('[smoke:correlation] Starting Day 19 correlation smoke test...');

  // 1. Topology validation
  const topoConfig = loadTopologyConfig();
  const topo = new TopologyIndex(topoConfig.links);
  console.log(`[smoke:correlation] ✓ TopologyIndex built: version=${topo.version}, cameras=${Object.keys(topoConfig.cameras).length}, links=${topoConfig.links.length}`);

  // 2. Bounds & routes check
  const routes0102 = topo.routesBetween('CAM-01', 'CAM-02');
  if (routes0102.length !== 1 || routes0102[0]!.typical_s !== 360) {
    throw new Error('Topology route CAM-01 -> CAM-02 unexpected');
  }
  console.log(`[smoke:correlation] ✓ Routes check: CAM-01 -> CAM-02 typical=${routes0102[0]!.typical_s}s`);

  // 3. Link evaluation check
  const cfg = loadCorrelationConfig();
  const makeS = (cam: string, t1: string, t2 = t1, plate = 'KA01AB1234'): Sighting => ({
    camera_id: cam,
    first_seen: t1,
    last_seen: t2,
    event_count: 1,
    max_score: 50,
    event_types: ['ANPR_MATCH'],
    event_ids: [`s-${cam}`],
    plates: [plate],
  });

  const s1 = makeS('CAM-01', '2026-11-01T10:00:00.000000Z');
  const s2 = makeS('CAM-02', '2026-11-01T10:06:00.000000Z'); // +360s
  const link = evaluateLink(s1, s2, topo, cfg);
  if (link.class !== 'PLAUSIBLE' || link.confidence !== 1.0) {
    throw new Error(`Link evaluation failed: class=${link.class}, conf=${link.confidence}`);
  }
  console.log(`[smoke:correlation] ✓ Link evaluation: CAM-01 -> CAM-02 class=${link.class}, confidence=${link.confidence}`);

  // 4. Correlate check
  const s3 = makeS('CAM-04', '2026-11-01T10:13:00.000000Z'); // +420s
  const corr = correlate([s1, s2, s3], topo, cfg);
  if (corr.trips.length !== 1 || corr.trips[0]!.trajectories.length !== 1 || corr.anomalies.length !== 0) {
    throw new Error('Correlation Scenario 3 verification failed');
  }
  console.log(`[smoke:correlation] ✓ Correlate Scenario 3: 1 trip, 1 trajectory, 0 anomalies`);

  // 5. Sequence search validation
  const cams = parseCameraSequence('CAM-01,CAM-02,CAM-04');
  const validHops = verifySequenceHops([
    { camera_id: 'CAM-01', timestamp: '2026-11-01T10:00:00.000000Z', event_id: 'e1' },
    { camera_id: 'CAM-02', timestamp: '2026-11-01T10:06:00.000000Z', event_id: 'e2' },
    { camera_id: 'CAM-04', timestamp: '2026-11-01T10:13:00.000000Z', event_id: 'e3' },
  ], 900);
  if (!validHops || cams.length !== 3) {
    throw new Error('Sequence parsing and verification failed');
  }
  console.log(`[smoke:correlation] ✓ Sequence verification: 3 camera hops valid within 900s`);

  console.log('[smoke:correlation] ALL SMOKE CHECKS PASSED SUCCESSFULLY! 🎯');
}

runCorrelationSmoke().catch(err => {
  console.error('[smoke:correlation] FAILED:', err);
  process.exit(1);
});

