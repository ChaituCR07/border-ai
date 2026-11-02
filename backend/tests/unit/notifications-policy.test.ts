import { describe, expect, it } from 'vitest';
import {
  type AlertCtx,
  type Route,
  type NotificationConfig,
  matchRoutes,
  groupKey,
  decide,
  domainAllowed,
  sanitizeHeader,
  backoffDelay,
} from '../../src/modules/notifications/policy.js';

describe('Notification Policy & Decision Logic', () => {
  const dummyRoute: Route = {
    name: 'test-route',
    match: { priority: ['CRITICAL', 'HIGH'] },
    recipients: ['sec@example.org'],
    mode: 'immediate',
    include: { plate: true, snapshot: true, journey: true, explanation: true },
  };

  const dummyConfig: NotificationConfig = {
    version: 1,
    from: 'test@border-ai.local',
    base_url: 'http://localhost:5173',
    display_timezone: 'UTC',
    catchup_max_age_s: 3600,
    cooldown_s: 300,
    rate_limit: { per_recipient_per_min: 6 },
    max_attempts: 6,
    routes: [
      dummyRoute,
      {
        name: 'cam1-only',
        match: { priority: ['CRITICAL'], camera_id: ['CAM-01'] },
        recipients: ['cam1@example.org'],
        mode: 'immediate',
        include: { plate: true, snapshot: false, journey: false, explanation: true },
      },
      {
        name: 'digest-high',
        match: { priority: ['HIGH'] },
        recipients: ['mgr@example.org'],
        mode: 'digest',
        digest_window_s: 600,
        include: { plate: true, snapshot: false, journey: false, explanation: true },
      },
    ],
  };

  const baseAlert: AlertCtx = {
    alert_id: 'a1',
    priority: 'CRITICAL',
    created_at: '2026-11-02T12:00:00Z',
    camera_id: 'CAM-01',
    event_type: 'RESTRICTED_ZONE_ENTRY',
    plate: 'KA01AB1234',
    person_related: false,
  };

  describe('matchRoutes', () => {
    it('matches routes by priority, camera_id, and event_type', () => {
      const matched = matchRoutes(dummyConfig, baseAlert);
      expect(matched.map(r => r.name)).toEqual(['test-route', 'cam1-only']);
    });

    it('returns empty array when no routes match', () => {
      const lowAlert: AlertCtx = { ...baseAlert, priority: 'LOW' };
      const matched = matchRoutes(dummyConfig, lowAlert);
      expect(matched).toHaveLength(0);
    });
  });

  describe('groupKey', () => {
    it('groups by camera and normalized plate', () => {
      const key1 = groupKey({ ...baseAlert, plate: 'KA01-AB-1234' });
      const key2 = groupKey({ ...baseAlert, plate: 'KA01AB1234' });
      const key3 = groupKey({ ...baseAlert, plate: 'KAO1AB1234' }); // OCR O -> 0
      expect(key1).toBe(key2);
      expect(key1).toBe(key3);
    });

    it('falls back to event_type when no plate is present', () => {
      const key = groupKey({ ...baseAlert, plate: null });
      expect(key).toBe('CAM-01|event:RESTRICTED_ZONE_ENTRY');
    });
  });

  describe('decide (Cooldown & Priority Upgrade Bypass)', () => {
    it('SENDs when no previous alert in group', () => {
      const res = decide(dummyRoute, baseAlert, null, 300);
      expect(res.action).toBe('SEND');
    });

    it('SKIPs when within cooldown and same priority', () => {
      const res = decide(dummyRoute, baseAlert, { created_at_age_s: 150, priority: 'CRITICAL' }, 300);
      expect(res.action).toBe('SKIP');
      if (res.action === 'SKIP') {
        expect(res.reason).toBe('cooldown');
      }
    });

    it('SENDs when cooldown has elapsed', () => {
      const res = decide(dummyRoute, baseAlert, { created_at_age_s: 301, priority: 'CRITICAL' }, 300);
      expect(res.action).toBe('SEND');
    });

    it('bypasses cooldown when priority upgrades (HIGH -> CRITICAL)', () => {
      const res = decide(
        dummyRoute,
        { ...baseAlert, priority: 'CRITICAL' },
        { created_at_age_s: 45, priority: 'HIGH' },
        300
      );
      expect(res.action).toBe('SEND');
    });

    it('does not bypass cooldown when priority downgrades or stays same', () => {
      const res = decide(
        dummyRoute,
        { ...baseAlert, priority: 'HIGH' },
        { created_at_age_s: 45, priority: 'CRITICAL' },
        300
      );
      expect(res.action).toBe('SKIP');
    });

    it('always SENDs for digest mode routes (delegating batching to worker)', () => {
      const digestRoute = dummyConfig.routes.find(r => r.mode === 'digest')!;
      const res = decide(digestRoute, baseAlert, { created_at_age_s: 10, priority: 'CRITICAL' }, 300);
      expect(res.action).toBe('SEND');
    });
  });

  describe('domainAllowed', () => {
    const allowed = ['example.org', 'border-ai.local'];

    it('permits exact allowed domains (case-insensitive)', () => {
      expect(domainAllowed('user@example.org', allowed)).toBe(true);
      expect(domainAllowed('USER@EXAMPLE.ORG', allowed)).toBe(true);
      expect(domainAllowed('alerts@border-ai.local', allowed)).toBe(true);
    });

    it('rejects disallowed domains and subdomains', () => {
      expect(domainAllowed('attacker@gmail.com', allowed)).toBe(false);
      expect(domainAllowed('user@sub.example.org', allowed)).toBe(false);
      expect(domainAllowed('malformed-address', allowed)).toBe(false);
    });
  });

  describe('sanitizeHeader', () => {
    it('strips newlines and carriage returns to prevent CRLF injection', () => {
      const injected = 'Subject line\r\nBcc: evil@hacker.com\nAnother line';
      const clean = sanitizeHeader(injected);
      expect(clean).toBe('Subject line Bcc: evil@hacker.com Another line');
      expect(clean).not.toContain('\r');
      expect(clean).not.toContain('\n');
    });

    it('enforces maximum length', () => {
      const long = 'A'.repeat(300);
      expect(sanitizeHeader(long, 50)).toHaveLength(50);
    });
  });

  describe('backoffDelay', () => {
    it('returns exponential backoff schedule delays', () => {
      expect(backoffDelay(1)).toBe(10);
      expect(backoffDelay(2)).toBe(30);
      expect(backoffDelay(3)).toBe(120);
      expect(backoffDelay(4)).toBe(600);
      expect(backoffDelay(5)).toBe(1800);
      expect(backoffDelay(6)).toBe(1800);
    });
  });
});
