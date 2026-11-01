import { Sighting, isoToMicros } from '../investigation/journey.js';
import { CorrelationConfig } from './config.js';
import { TopologyIndex, Route } from './topology.js';

export type LinkClass =
  | 'REVISIT'
  | 'PLAUSIBLE'
  | 'FAST'
  | 'SLOW'
  | 'IMPOSSIBLE'
  | 'SIMULTANEOUS'
  | 'OVERLAP_OK'
  | 'UNLINKED';

export interface Factor {
  name: 'plate' | 'timing' | 'appearance';
  value: number;
  detail: string;
}

export interface Link {
  from_camera: string;
  to_camera: string;
  gap_s: number;
  class: LinkClass;
  confidence: number; // 0..1
  factors: Factor[];
  expected: { min_s: number; typical_s: number; max_s: number } | null;
  missed_cameras: string[];
}

export function round3(n: number): number {
  return Math.round(n * 1000) / 1000;
}

export function fmt(seconds: number): string {
  const s = Math.round(seconds);
  if (s <= 60) return `${s} s`;
  const m = Math.floor(s / 60);
  const remS = s % 60;
  if (s < 3600) {
    return remS === 0 ? `${m} min` : `${m} min ${remS} s`;
  }
  const h = Math.floor(s / 3600);
  const remM = Math.floor((s % 3600) / 60);
  return `${h} h ${String(remM).padStart(2, '0')} min`;
}

export function closest(routes: Route[], gap: number): Route {
  if (!routes.length) {
    throw new Error('Cannot find closest route on empty routes array');
  }
  return [...routes].sort((a, b) => {
    const diffA = Math.abs(a.typical_s - gap);
    const diffB = Math.abs(b.typical_s - gap);
    if (diffA !== diffB) return diffA - diffB;
    if (a.cameras.length !== b.cameras.length) return a.cameras.length - b.cameras.length;
    return a.cameras.join().localeCompare(b.cameras.join());
  })[0]!;
}

export function plateFactor(a: Sighting, b: Sighting, cfg: CorrelationConfig): Factor {
  const qA = a.plate_quality ?? (a.plates.length > 1 ? 'lookalike' : 'exact');
  const qB = b.plate_quality ?? (b.plates.length > 1 ? 'lookalike' : 'exact');

  let quality: 'exact' | 'lookalike' | 'unknown' = 'exact';
  if (qA === 'lookalike' || qB === 'lookalike') {
    quality = 'lookalike';
  } else if (qA === 'unknown' || qB === 'unknown') {
    quality = 'unknown';
  }

  const value = cfg.plate_conf[quality] ?? 1.0;
  let detail = 'exact match';
  if (quality === 'lookalike') {
    const variants = Array.from(new Set([...(a.plates || []), ...(b.plates || [])]));
    detail = `look-alike variant ${variants.join(', ')}`;
  } else if (quality === 'unknown') {
    detail = 'unknown plate quality';
  }

  return { name: 'plate', value, detail };
}

export function evaluateLink(a: Sighting, b: Sighting, topo: TopologyIndex, cfg: CorrelationConfig): Link {
  const gap = Number(isoToMicros(b.first_seen) - isoToMicros(a.last_seen)) / 1_000_000;
  const plate = plateFactor(a, b, cfg);

  const done = (
    cls: LinkClass,
    timing: number,
    detail: string,
    expected: Link['expected'] = null,
    missed: string[] = []
  ): Link => ({
    from_camera: a.camera_id,
    to_camera: b.camera_id,
    gap_s: round3(gap),
    class: cls,
    confidence: round3(plate.value * timing),
    factors: [plate, { name: 'timing', value: timing, detail }],
    expected,
    missed_cameras: missed,
  });

  if (a.camera_id === b.camera_id) {
    return done('REVISIT', 1.0, `returned to ${b.camera_id} after ${fmt(gap)}`);
  }

  if (gap < 0) {
    if (topo.hasOverlap(a.camera_id, b.camera_id) && gap >= -cfg.overlap_tolerance_s) {
      return done('OVERLAP_OK', 1.0, `overlapping coverage between ${a.camera_id} and ${b.camera_id}`);
    }
    return done('SIMULTANEOUS', 0, `seen at ${b.camera_id} ${fmt(-gap)} before leaving ${a.camera_id}`);
  }

  const routes = topo.routesBetween(a.camera_id, b.camera_id);
  if (!routes.length) {
    return done('UNLINKED', cfg.timing_conf.unlinked, `no known route ${a.camera_id} → ${b.camera_id}`);
  }

  const lower = Math.min(...routes.map(r => r.min_s));
  const upper = Math.max(...routes.map(r => r.max_s));
  const tol = cfg.speed_tolerance; // e.g. 0.8
  const expected = { min_s: lower, typical_s: closest(routes, gap).typical_s, max_s: upper };
  const range = `expected ${fmt(lower)}–${fmt(upper)}`;

  if (gap < tol * lower) {
    return done('IMPOSSIBLE', 0, `${fmt(gap)} is far below the fastest route (${fmt(lower)})`, expected);
  }

  // cameras that EVERY consistent route passes through but where nothing was seen
  const consistent = routes.filter(r => gap >= tol * r.min_s && gap <= r.max_s);
  const missed =
    consistent.length && consistent.every(r => r.intermediates.length)
      ? consistent[0]!.intermediates.filter(c => consistent.every(r => r.intermediates.includes(c)))
      : [];

  if (gap < lower) {
    return done('FAST', cfg.timing_conf.fast, `${fmt(gap)} is slightly faster than the fastest route (${fmt(lower)})`, expected, missed);
  }

  if (gap <= upper) {
    const best = closest(routes, gap);
    const inBand = gap >= 0.75 * best.typical_s && gap <= 1.5 * best.typical_s;
    const inside = routes.some(r => gap >= r.min_s && gap <= r.max_s);
    const t = inside && inBand ? cfg.timing_conf.typical : cfg.timing_conf.in_range;
    return done('PLAUSIBLE', t, `${fmt(gap)} within ${range}`, expected, missed);
  }

  const t = gap <= 3 * upper ? cfg.timing_conf.slow_near : cfg.timing_conf.slow_far;
  return done('SLOW', t, `${fmt(gap)} exceeds the expected maximum (${fmt(upper)})`, expected);
}
