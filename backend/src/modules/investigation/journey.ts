export interface EventLite {
  event_id: string;
  camera_id: string;
  event_type: string;
  timestamp: string; // ISO with microsecond precision
  threat_score: number;
  plate: string | null;
  plate_match?: string;
}

export interface Sighting {
  camera_id: string;
  first_seen: string;
  last_seen: string;
  event_count: number;
  max_score: number;
  event_types: string[];
  event_ids: string[];
  plates: string[]; // plate variants seen here (OCR variants)
}

export interface Transition {
  from: string;
  to: string;
  gap_s: number;
}

export interface Journey {
  sightings: Sighting[];
  transitions: Transition[];
  total_events: number;
  span_s: number;
  plate_variants: string[];
}

/**
 * Converts ISO 8601 UTC timestamp to microseconds since Unix epoch.
 * Preserves sub-millisecond fidelity (ADR 0015).
 */
export function isoToMicros(iso: string): bigint {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z?$/.exec(iso);
  if (!m) throw new Error(`Invalid ISO timestamp: ${iso}`);
  const secs = Date.UTC(+m[1]!, +m[2]! - 1, +m[3]!, +m[4]!, +m[5]!, +m[6]!) / 1000;
  return BigInt(secs) * 1_000_000n + BigInt((m[7] ?? '').padEnd(6, '0') || '0');
}

/**
 * Pure function to construct a vehicle journey from chronological sightings (Task 5).
 * Collapses consecutive same-camera events within mergeGapS (default 120s).
 */
export function buildJourney(events: EventLite[], opts: { mergeGapS?: number } = {}): Journey {
  if (events.length === 0) {
    return { sightings: [], transitions: [], total_events: 0, span_s: 0, plate_variants: [] };
  }

  const mergeGap = BigInt(Math.round((opts.mergeGapS ?? 120) * 1_000_000));

  // Sort by microsecond timestamp ASC, tie-breaking deterministically on event_id
  const sorted = [...events].sort((a, b) => {
    const d = isoToMicros(a.timestamp) - isoToMicros(b.timestamp);
    return d < 0n ? -1 : d > 0n ? 1 : a.event_id.localeCompare(b.event_id);
  });

  const sightings: Sighting[] = [];

  for (const e of sorted) {
    const last = sightings.at(-1);
    const t = isoToMicros(e.timestamp);

    if (last && last.camera_id === e.camera_id && t - isoToMicros(last.last_seen) <= mergeGap) {
      last.last_seen = e.timestamp;
      last.event_count += 1;
      last.max_score = Math.max(last.max_score, e.threat_score);
      if (!last.event_types.includes(e.event_type)) last.event_types.push(e.event_type);
      last.event_ids.push(e.event_id);
      if (e.plate && !last.plates.includes(e.plate)) last.plates.push(e.plate);
    } else {
      sightings.push({
        camera_id: e.camera_id,
        first_seen: e.timestamp,
        last_seen: e.timestamp,
        event_count: 1,
        max_score: e.threat_score,
        event_types: [e.event_type],
        event_ids: [e.event_id],
        plates: e.plate ? [e.plate] : [],
      });
    }
  }

  const transitions: Transition[] = sightings.slice(1).map((s, i) => ({
    from: sightings[i]!.camera_id,
    to: s.camera_id,
    gap_s: Number(isoToMicros(s.first_seen) - isoToMicros(sightings[i]!.last_seen)) / 1_000_000,
  }));

  const span_s = sightings.length
    ? Number(isoToMicros(sightings.at(-1)!.last_seen) - isoToMicros(sightings[0]!.first_seen)) / 1_000_000
    : 0;

  const plate_variants = Array.from(new Set(sightings.flatMap(s => s.plates)));

  return {
    sightings,
    transitions,
    total_events: events.length,
    span_s,
    plate_variants,
  };
}
