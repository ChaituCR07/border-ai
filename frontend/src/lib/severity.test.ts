import { describe, it, expect } from 'vitest';
import {
  SEVERITY_ORDER,
  SEVERITY_META,
  compareSeverityDesc,
  getSeverityMeta,
} from './severity';

describe('severity model', () => {
  it('defines the 4 required severity ranks in descending priority', () => {
    expect(SEVERITY_ORDER).toEqual(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']);
    expect(SEVERITY_META.CRITICAL.rank).toBe(4);
    expect(SEVERITY_META.HIGH.rank).toBe(3);
    expect(SEVERITY_META.MEDIUM.rank).toBe(2);
    expect(SEVERITY_META.LOW.rank).toBe(1);
  });

  it('correctly sorts severities in descending order', () => {
    expect(compareSeverityDesc('CRITICAL', 'HIGH')).toBeLessThan(0);
    expect(compareSeverityDesc('LOW', 'CRITICAL')).toBeGreaterThan(0);
    expect(compareSeverityDesc('MEDIUM', 'MEDIUM')).toBe(0);
  });

  it('handles unknown or unexpected server enum values safely without crashing', () => {
    const meta = getSeverityMeta('UNKNOWN_PRIORITY_FROM_NEW_BACKEND' as any);
    expect(meta).toBeDefined();
    expect(meta.label).toBe('Unknown');
    expect(meta.rank).toBe(0);
  });
});
