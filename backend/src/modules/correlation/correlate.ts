import { Sighting, isoToMicros } from '../investigation/journey.js';
import { CorrelationConfig } from './config.js';
import { TopologyIndex } from './topology.js';
import { Link, evaluateLink, fmt, round3 } from './link.js';

export type AnomalyType =
  | 'IMPOSSIBLE_TRAVEL'
  | 'SIMULTANEOUS_SIGHTINGS'
  | 'MULTIPLE_TRAJECTORIES'
  | 'MISSED_CAMERA'
  | 'SLOW_TRANSIT'
  | 'FAST_TRANSIT'
  | 'UNLINKED_HOP'
  | 'TRAJECTORY_OVERFLOW';

export interface Trajectory {
  id: string; // T1, T2 … ordered by first_seen
  sightings: Sighting[];
  links: Link[]; // links.length === sightings.length - 1
  confidence: number; // weakest link; 1 for single-sighting trajectories
  mean_confidence: number;
  cameras: string[];
}

export interface Trip {
  trip_id: string;
  start: string;
  end: string;
  trajectories: Trajectory[];
}

export interface Anomaly {
  type: AnomalyType;
  severity: 'info' | 'warning';
  trip_id: string;
  trajectory_ids: string[];
  message: string;
  evidence: Record<string, unknown>;
}

export interface CorrelationResult {
  topology_version: string;
  config_version: number;
  trips: Trip[];
  anomalies: Anomaly[];
}

export function bySeen(a: Sighting, b: Sighting): number {
  const diff = isoToMicros(a.first_seen) - isoToMicros(b.first_seen);
  if (diff !== 0n) return diff < 0n ? -1 : 1;
  const camDiff = a.camera_id.localeCompare(b.camera_id);
  if (camDiff !== 0) return camDiff;
  const aEvt = a.event_ids[0] ?? '';
  const bEvt = b.event_ids[0] ?? '';
  return aEvt.localeCompare(bEvt);
}

function lastSeen(t: { sightings: Sighting[]; links: Link[] }): bigint {
  return isoToMicros(t.sightings.at(-1)!.last_seen);
}

function finish(id: string, t: { sightings: Sighting[]; links: Link[] }): Trajectory {
  const conf =
    t.links.length === 0
      ? 1.0
      : round3(Math.min(...t.links.map(l => l.confidence)));
  const meanConf =
    t.links.length === 0
      ? 1.0
      : round3(t.links.reduce((acc, l) => acc + l.confidence, 0) / t.links.length);

  return {
    id,
    sightings: t.sightings,
    links: t.links,
    confidence: conf,
    mean_confidence: meanConf,
    cameras: t.sightings.map(s => s.camera_id),
  };
}

function maxLastSeenIso(group: Sighting[]): string {
  let maxMicros = -1n;
  let maxIso = group[0]!.last_seen;
  for (const s of group) {
    const m = isoToMicros(s.last_seen);
    if (m > maxMicros) {
      maxMicros = m;
      maxIso = s.last_seen;
    }
  }
  return maxIso;
}

function impossibleAnomaly(
  trip_id: string,
  trajs: { sightings: Sighting[]; links: Link[] }[],
  s: Sighting,
  topo: TopologyIndex,
  cfg: CorrelationConfig
): Anomaly {
  // Find the most recently seen trajectory
  let closestT = trajs[0]!;
  let closestIdx = 0;
  for (let idx = 0; idx < trajs.length; idx++) {
    const t = trajs[idx]!;
    if (lastSeen(t) > lastSeen(closestT)) {
      closestT = t;
      closestIdx = idx;
    }
  }

  const prev = closestT.sightings.at(-1)!;
  const link = evaluateLink(prev, s, topo, cfg);
  const trajId = `T${closestIdx + 1}`;

  if (link.class === 'SIMULTANEOUS') {
    return {
      type: 'SIMULTANEOUS_SIGHTINGS',
      severity: 'warning',
      trip_id,
      trajectory_ids: [trajId],
      message: `Simultaneous sighting: seen at ${s.camera_id} while still recorded at ${prev.camera_id}`,
      evidence: {
        from_camera: prev.camera_id,
        to_camera: s.camera_id,
        gap_s: link.gap_s,
        first_seen: s.first_seen,
        last_seen: prev.last_seen,
      },
    };
  }

  const lowerBoundStr = link.expected ? fmt(link.expected.min_s) : 'unknown';
  return {
    type: 'IMPOSSIBLE_TRAVEL',
    severity: 'warning',
    trip_id,
    trajectory_ids: [trajId],
    message: `Impossible travel: ${s.camera_id} reached in ${fmt(link.gap_s)} from ${prev.camera_id}, fastest route requires at least ${lowerBoundStr}`,
    evidence: {
      from_camera: prev.camera_id,
      to_camera: s.camera_id,
      gap_s: link.gap_s,
      min_expected_s: link.expected?.min_s ?? null,
      expected: link.expected,
      first_seen: s.first_seen,
      last_seen: prev.last_seen,
    },
  };
}

function overflowAnomaly(trip_id: string, s: Sighting, link: Link): Anomaly {
  return {
    type: 'TRAJECTORY_OVERFLOW',
    severity: 'warning',
    trip_id,
    trajectory_ids: [],
    message: `Trajectory limit reached; attached sighting at ${s.camera_id} to closest trajectory`,
    evidence: {
      camera_id: s.camera_id,
      timestamp: s.first_seen,
      link_class: link.class,
    },
  };
}

function linkAnomalies(trip_id: string, trajectories: Trajectory[]): Anomaly[] {
  const anomalies: Anomaly[] = [];

  for (const t of trajectories) {
    for (const link of t.links) {
      if (link.missed_cameras.length > 0) {
        anomalies.push({
          type: 'MISSED_CAMERA',
          severity: 'info',
          trip_id,
          trajectory_ids: [t.id],
          message: `Missed expected camera(s) ${link.missed_cameras.join(', ')} between ${link.from_camera} and ${link.to_camera}`,
          evidence: {
            from_camera: link.from_camera,
            to_camera: link.to_camera,
            gap_s: link.gap_s,
            missed_cameras: link.missed_cameras,
          },
        });
      }

      if (link.class === 'SLOW') {
        anomalies.push({
          type: 'SLOW_TRANSIT',
          severity: 'info',
          trip_id,
          trajectory_ids: [t.id],
          message: `Slow transit between ${link.from_camera} and ${link.to_camera} (${fmt(link.gap_s)})`,
          evidence: {
            from_camera: link.from_camera,
            to_camera: link.to_camera,
            gap_s: link.gap_s,
            expected: link.expected,
          },
        });
      } else if (link.class === 'FAST') {
        anomalies.push({
          type: 'FAST_TRANSIT',
          severity: 'info',
          trip_id,
          trajectory_ids: [t.id],
          message: `Fast transit between ${link.from_camera} and ${link.to_camera} (${fmt(link.gap_s)})`,
          evidence: {
            from_camera: link.from_camera,
            to_camera: link.to_camera,
            gap_s: link.gap_s,
            expected: link.expected,
          },
        });
      } else if (link.class === 'UNLINKED') {
        anomalies.push({
          type: 'UNLINKED_HOP',
          severity: 'info',
          trip_id,
          trajectory_ids: [t.id],
          message: `Unlinked hop between ${link.from_camera} and ${link.to_camera}`,
          evidence: {
            from_camera: link.from_camera,
            to_camera: link.to_camera,
            gap_s: link.gap_s,
          },
        });
      }
    }
  }

  return anomalies;
}

function multipleTrajectoriesAnomaly(trip_id: string, trajectories: Trajectory[]): Anomaly {
  return {
    type: 'MULTIPLE_TRAJECTORIES',
    severity: 'warning',
    trip_id,
    trajectory_ids: trajectories.map(t => t.id),
    message: `Multiple simultaneous or disjoint trajectories detected (${trajectories.length}): possible duplicate plate or misread`,
    evidence: {
      count: trajectories.length,
      trajectory_ids: trajectories.map(t => t.id),
    },
  };
}

function sortAnomalies(anomalies: Anomaly[]): Anomaly[] {
  return [...anomalies].sort((a, b) => {
    // Warning severity before info
    if (a.severity !== b.severity) {
      return a.severity === 'warning' ? -1 : 1;
    }
    // Then by trip_id
    const tripDiff = a.trip_id.localeCompare(b.trip_id);
    if (tripDiff !== 0) return tripDiff;
    // Then by type
    const typeDiff = a.type.localeCompare(b.type);
    if (typeDiff !== 0) return typeDiff;
    // Then by message
    return a.message.localeCompare(b.message);
  });
}

export function correlate(
  sightings: Sighting[],
  topo: TopologyIndex,
  cfg: CorrelationConfig
): CorrelationResult {
  const sorted = [...sightings].sort(bySeen); // Never mutate caller's array
  const tripGroups: Sighting[][] = [];
  let tripLastSeen = 0n;

  for (const s of sorted) {
    const first = isoToMicros(s.first_seen);
    const cur = tripGroups.at(-1);
    if (!cur || Number(first - tripLastSeen) / 1e6 > cfg.trip_break_s) {
      tripGroups.push([s]);
      tripLastSeen = isoToMicros(s.last_seen);
    } else {
      cur.push(s);
      const l = isoToMicros(s.last_seen);
      if (l > tripLastSeen) tripLastSeen = l;
    }
  }

  const anomalies: Anomaly[] = [];
  const trips = tripGroups.map((group, i): Trip => {
    const trip_id = `trip-${i + 1}`;
    const trajs: { sightings: Sighting[]; links: Link[] }[] = [];

    for (const s of group) {
      let best: { t: (typeof trajs)[number]; link: Link } | null = null;
      for (const t of trajs) {
        const link = evaluateLink(t.sightings.at(-1)!, s, topo, cfg);
        if (link.class === 'IMPOSSIBLE' || link.class === 'SIMULTANEOUS') continue;
        if (link.confidence < cfg.min_link_confidence) continue;

        if (!best) {
          best = { t, link };
        } else if (link.confidence > best.link.confidence) {
          best = { t, link };
        } else if (link.confidence === best.link.confidence) {
          // Prefer link without missed cameras
          if (link.missed_cameras.length !== best.link.missed_cameras.length) {
            if (link.missed_cameras.length < best.link.missed_cameras.length) {
              best = { t, link };
            }
          } else {
            // Prefer link closer to typical travel time
            const devCur = link.expected ? Math.abs(link.gap_s - link.expected.typical_s) : Infinity;
            const devBest = best.link.expected ? Math.abs(best.link.gap_s - best.link.expected.typical_s) : Infinity;
            if (devCur !== devBest) {
              if (devCur < devBest) {
                best = { t, link };
              }
            } else if (lastSeen(t) > lastSeen(best.t)) {
              // Tie-breaker: recency
              best = { t, link };
            }
          }
        }
      }

      if (best) {
        best.t.sightings.push(s);
        best.t.links.push(best.link);
        continue;
      }

      if (trajs.length >= cfg.max_trajectories) {
        // Overflow: attach to the closest-in-time trajectory
        const t = trajs.reduce((a, b) => (lastSeen(b) > lastSeen(a) ? b : a));
        const link = evaluateLink(t.sightings.at(-1)!, s, topo, cfg);
        t.sightings.push(s);
        t.links.push(link);
        anomalies.push(overflowAnomaly(trip_id, s, link));
        continue;
      }

      if (trajs.length) {
        anomalies.push(impossibleAnomaly(trip_id, trajs, s, topo, cfg));
      }
      trajs.push({ sightings: [s], links: [] });
    }

    const trajectories = trajs.map((t, k): Trajectory => finish(`T${k + 1}`, t));
    anomalies.push(...linkAnomalies(trip_id, trajectories));
    if (trajectories.length >= 2) {
      anomalies.push(multipleTrajectoriesAnomaly(trip_id, trajectories));
    }

    return {
      trip_id,
      start: group[0]!.first_seen,
      end: maxLastSeenIso(group),
      trajectories,
    };
  });

  return {
    topology_version: topo.version,
    config_version: cfg.version,
    trips,
    anomalies: sortAnomalies(anomalies),
  };
}
