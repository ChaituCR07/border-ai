import { AppError } from './errors.js';

/**
 * Converts a PostgreSQL timestamptz string (or standard timestamp) to an ISO-8601 UTC string with microseconds.
 * E.g.: '2026-10-25 02:13:42.123456+00' -> '2026-10-25T02:13:42.123456Z'
 */
export function pgTsToIso(v: string | null | undefined): string | null {
  if (!v) return null;
  const trimmed = v.trim();
  if (trimmed.endsWith('Z')) return trimmed;

  // Handle 'YYYY-MM-DD HH:mm:ss.ssssss+00' or 'YYYY-MM-DD HH:mm:ss.ssssss+00:00'
  const tzMatch = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?:\+00(?::00)?)?$/.exec(trimmed);
  if (tzMatch && tzMatch[1] && tzMatch[2]) {
    return `${tzMatch[1]}T${tzMatch[2]}Z`;
  }

  // Fallback to JS Date parse if standard ISO
  const d = new Date(trimmed);
  if (!isNaN(d.getTime())) {
    return d.toISOString();
  }

  throw new Error(`Unexpected timestamp format: ${v}`);
}

/**
 * Validates a query time range:
 * - from and to must be valid ISO dates
 * - from must be strictly before to
 * - maximum allowed span is 90 days to prevent runaway table scans
 */
export function validateTimeRange(from?: string, to?: string): void {
  if (from && isNaN(Date.parse(from))) {
    throw new AppError(400, 'VALIDATION_ERROR', "Invalid 'from' timestamp: must be valid ISO-8601");
  }
  if (to && isNaN(Date.parse(to))) {
    throw new AppError(400, 'VALIDATION_ERROR', "Invalid 'to' timestamp: must be valid ISO-8601");
  }
  if (from && to) {
    const fromMs = new Date(from).getTime();
    const toMs = new Date(to).getTime();
    if (fromMs >= toMs) {
      throw new AppError(400, 'VALIDATION_ERROR', "'from' timestamp must be strictly earlier than 'to' timestamp");
    }
    const maxSpanMs = 90 * 24 * 60 * 60 * 1000;
    if (toMs - fromMs > maxSpanMs) {
      throw new AppError(400, 'VALIDATION_ERROR', 'Time range cannot exceed 90 days');
    }
  }
}
