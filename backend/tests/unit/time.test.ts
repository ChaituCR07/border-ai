import { describe, it, expect } from 'vitest';
import { pgTsToIso, validateTimeRange } from '../../src/common/time.js';
import { AppError } from '../../src/common/errors.js';

describe('Time utilities', () => {
  it('converts postgres timestamptz string with microseconds to ISO-8601 UTC', () => {
    const raw = '2026-10-25 02:13:42.123456+00';
    expect(pgTsToIso(raw)).toBe('2026-10-25T02:13:42.123456Z');
  });

  it('handles standard ISO format cleanly', () => {
    const iso = '2026-10-25T02:13:42.123456Z';
    expect(pgTsToIso(iso)).toBe(iso);
  });

  it('returns null for null or empty input', () => {
    expect(pgTsToIso(null)).toBeNull();
    expect(pgTsToIso(undefined)).toBeNull();
  });

  it('validates time ranges correctly', () => {
    expect(() => validateTimeRange('2026-10-01T00:00:00Z', '2026-10-10T00:00:00Z')).not.toThrow();
  });

  it('rejects from >= to with VALIDATION_ERROR', () => {
    expect(() => validateTimeRange('2026-10-10T00:00:00Z', '2026-10-01T00:00:00Z')).toThrow(AppError);
    expect(() => validateTimeRange('2026-10-01T00:00:00Z', '2026-10-01T00:00:00Z')).toThrow(AppError);
  });

  it('rejects time ranges exceeding 90 days', () => {
    const from = '2026-01-01T00:00:00Z';
    const to = '2026-06-01T00:00:00Z'; // > 90 days
    expect(() => validateTimeRange(from, to)).toThrow(AppError);
  });
});
