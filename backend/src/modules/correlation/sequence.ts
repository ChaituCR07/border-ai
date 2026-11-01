import { z } from 'zod';
import { AppError } from '../../common/errors.js';
import { isoToMicros } from '../investigation/journey.js';

export const CAMERA_ID_REGEX = /^[A-Za-z0-9_-]{2,32}$/;

export const SequenceQuerySchema = z.object({
  cams: z.string().min(1),
  from: z.string().datetime({ offset: true }),
  to: z.string().datetime({ offset: true }),
  max_hop_gap_s: z.coerce.number().int().min(1).max(86400).default(900),
  limit: z.coerce.number().int().min(1).max(50).default(50),
  purpose: z.string().min(5, 'purpose must be at least 5 characters long'),
});

export type SequenceQuery = z.infer<typeof SequenceQuerySchema>;

export interface SequenceHop {
  camera_id: string;
  timestamp: string;
  event_id: string;
}

export interface SequenceMatch {
  plate_key: string;
  representative_plate: string;
  plate_variants: string[];
  hops: SequenceHop[];
  total_duration_s: number;
}

export interface SequenceSearchResponse {
  data: SequenceMatch[];
  meta: {
    steps: number;
    cameras: string[];
    total: number;
    limit: number;
  };
}

export function parseCameraSequence(camsStr: string): string[] {
  const parts = camsStr.split(',').map(s => s.trim()).filter(Boolean);
  if (parts.length < 2 || parts.length > 5) {
    throw new AppError(400, 'VALIDATION_ERROR', 'Sequence search requires between 2 and 5 camera steps');
  }
  for (const cam of parts) {
    if (!CAMERA_ID_REGEX.test(cam)) {
      throw new AppError(400, 'VALIDATION_ERROR', `Invalid camera identifier '${cam}'`);
    }
  }
  return parts;
}

export function sequenceSql(steps: number): string {
  const ctes = Array.from(
    { length: steps },
    (_, i) => `
    s${i + 1} AS (
      SELECT plate_key, plate_norm, "timestamp" AS ts, event_id
        FROM events
       WHERE camera_id = $${i + 1} AND plate_key IS NOT NULL
         AND "timestamp" >= $${steps + 1}::timestamptz AND "timestamp" < $${steps + 2}::timestamptz)`
  );

  const joins = Array.from(
    { length: steps - 1 },
    (_, i) => `
    JOIN s${i + 2} ON s${i + 2}.plate_key = s${i + 1}.plate_key
                  AND s${i + 2}.ts >  s${i + 1}.ts
                  AND s${i + 2}.ts <= s${i + 1}.ts + make_interval(secs => $${steps + 3})`
  );

  return `WITH ${ctes.join(',')}
    SELECT s1.plate_key,
           array_agg(DISTINCT s1.plate_norm) AS variants_first,
           min(s1.ts) AS first_ts,
           ${Array.from({ length: steps }, (_, i) => `min(s${i + 1}.ts) AS ts${i + 1}`).join(', ')}
      FROM s1 ${joins.join('')}
     GROUP BY s1.plate_key
     ORDER BY first_ts DESC
     LIMIT $${steps + 4}`;
}

export function verifySequenceHops(hops: SequenceHop[], maxHopGapS: number): boolean {
  if (hops.length < 2) return false;
  for (let i = 0; i < hops.length - 1; i++) {
    const curMicros = isoToMicros(hops[i]!.timestamp);
    const nextMicros = isoToMicros(hops[i + 1]!.timestamp);
    const gapS = Number(nextMicros - curMicros) / 1_000_000;
    if (gapS <= 0 || gapS > maxHopGapS) {
      return false;
    }
  }
  return true;
}
