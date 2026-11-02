import { describe, expect, it } from 'vitest';
import {
  NotificationConfigSchema,
  validateNotificationConfig,
  type NotificationConfig,
} from '../../src/modules/notifications/config.js';

describe('Notification Configuration & Validation', () => {
  const validBaseConfig: NotificationConfig = {
    version: 1,
    from: 'Border-AI Alerts <alerts@border-ai.local>',
    base_url: 'http://localhost:5173',
    display_timezone: 'UTC',
    catchup_max_age_s: 3600,
    cooldown_s: 300,
    rate_limit: { per_recipient_per_min: 6 },
    max_attempts: 6,
    routes: [
      {
        name: 'critical-alerts',
        match: { priority: ['CRITICAL'] },
        recipients: ['duty@example.org'],
        mode: 'immediate',
        include: { plate: true, snapshot: true, journey: true, explanation: true },
        escalate: { after_s: 300, recipients: ['lead@example.org'] },
      },
    ],
  };

  it('validates a correct notification configuration', () => {
    const parsed = NotificationConfigSchema.parse(validBaseConfig);
    expect(parsed.routes).toHaveLength(1);
    const res = validateNotificationConfig(parsed, ['example.org']);
    expect(res.valid).toBe(true);
    expect(res.errors).toHaveLength(0);
  });

  it('rejects invalid email recipients', () => {
    const invalid = {
      ...validBaseConfig,
      routes: [
        {
          ...validBaseConfig.routes[0]!,
          recipients: ['not-an-email'],
        },
      ],
    };
    expect(() => NotificationConfigSchema.parse(invalid)).toThrow();
  });

  it('rejects digest route without digest_window_s', () => {
    const invalid = {
      ...validBaseConfig,
      routes: [
        {
          ...validBaseConfig.routes[0]!,
          mode: 'digest',
          digest_window_s: undefined,
        },
      ],
    };
    expect(() => NotificationConfigSchema.parse(invalid)).toThrow();
  });

  it('rejects escalation after_s below 30 seconds', () => {
    const invalid = {
      ...validBaseConfig,
      routes: [
        {
          ...validBaseConfig.routes[0]!,
          escalate: { after_s: 10, recipients: ['esc@example.org'] },
        },
      ],
    };
    expect(() => NotificationConfigSchema.parse(invalid)).toThrow();
  });

  it('warns when escalate is configured on a non-CRITICAL route', () => {
    const config: NotificationConfig = {
      ...validBaseConfig,
      routes: [
        {
          ...validBaseConfig.routes[0]!,
          match: { priority: ['HIGH'] },
          escalate: { after_s: 120, recipients: ['esc@example.org'] },
        },
      ],
    };
    const res = validateNotificationConfig(config, ['example.org']);
    expect(res.warnings.some(w => w.includes('does not include CRITICAL'))).toBe(true);
  });

  it('warns when all recipients are outside allowed domains', () => {
    const config: NotificationConfig = {
      ...validBaseConfig,
      routes: [
        {
          ...validBaseConfig.routes[0]!,
          recipients: ['external@gmail.com'],
        },
      ],
    };
    const res = validateNotificationConfig(config, ['example.org', 'border-ai.local']);
    expect(res.warnings.some(w => w.includes('NOTIFY_ALLOWED_DOMAINS'))).toBe(true);
  });

  it('detects duplicate route names', () => {
    const config: NotificationConfig = {
      ...validBaseConfig,
      routes: [
        validBaseConfig.routes[0]!,
        { ...validBaseConfig.routes[0]!, recipients: ['other@example.org'] },
      ],
    };
    const res = validateNotificationConfig(config, ['example.org']);
    expect(res.valid).toBe(false);
    expect(res.errors.some(e => e.includes('Duplicate route name'))).toBe(true);
  });
});
