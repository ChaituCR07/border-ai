import { describe, it, expect } from 'vitest';
import { relativeTime, formatTime } from './time';

describe('time formatting utilities', () => {
  it('formats relative times across boundaries', () => {
    const now = 1700000000000;
    expect(relativeTime(new Date(now).toISOString(), now)).toBe('0s ago');
    expect(relativeTime(new Date(now - 15000).toISOString(), now)).toBe('15s ago');
    expect(relativeTime(new Date(now - 59000).toISOString(), now)).toBe('59s ago');
    expect(relativeTime(new Date(now - 60000).toISOString(), now)).toBe('1m ago');
    expect(relativeTime(new Date(now - 3599000).toISOString(), now)).toBe('59m ago');
    expect(relativeTime(new Date(now - 3600000).toISOString(), now)).toBe('1h ago');
    expect(relativeTime(new Date(now - 86400000).toISOString(), now)).toBe('1d ago');
  });

  it('formats explicit timezone tags in UTC mode', () => {
    const iso = '2026-10-26T12:00:00.000000Z';
    const formatted = formatTime(iso, 'UTC');
    expect(formatted).toContain('12:00:00');
    expect(formatted).toContain('UTC');
  });
});
