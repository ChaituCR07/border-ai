import { describe, expect, it, vi } from 'vitest';
import {
  planOne,
  type PlannerDeps,
} from '../../src/modules/notifications/planner.js';
import {
  type NotificationConfig,
} from '../../src/modules/notifications/config.js';
import { type AlertCtx } from '../../src/modules/notifications/policy.js';

describe('Notification Planner Unit Tests (Mock DB Client)', () => {
  const testConfig: NotificationConfig = {
    version: 1,
    from: 'alerts@border-ai.local',
    base_url: 'http://localhost:5173',
    display_timezone: 'UTC',
    catchup_max_age_s: 3600,
    cooldown_s: 300,
    rate_limit: { per_recipient_per_min: 6 },
    max_attempts: 6,
    routes: [
      {
        name: 'critical-main',
        match: { priority: ['CRITICAL'] },
        recipients: ['control@example.org'],
        mode: 'immediate',
        include: { plate: true, snapshot: true, journey: true, explanation: true },
        escalate: { after_s: 300, recipients: ['duty@example.org'] },
      },
    ],
  };

  const defaultDeps: PlannerDeps = {
    allowedDomains: ['example.org', 'border-ai.local'],
    dryRun: false,
    enabled: true,
  };

  const criticalAlert: AlertCtx = {
    alert_id: 'alt-101',
    priority: 'CRITICAL',
    created_at: '2026-11-02T10:00:00Z',
    camera_id: 'CAM-01',
    event_type: 'ZONE_INTRUSION',
    plate: 'KA01AB1234',
    person_related: false,
  };

  function createMockClient() {
    const executedQueries: Array<{ sql: string; values: any[] }> = [];
    const client = {
      query: vi.fn(async (sql: string, values: any[] = []) => {
        executedQueries.push({ sql, values });
        // Mock lastInGroup check returning empty (no previous alert)
        if (sql.includes('SELECT priority') && sql.includes('notifications')) {
          return { rows: [] };
        }
        // Mock insert returning 1
        if (sql.includes('INSERT INTO notifications')) {
          return { rowCount: 1, rows: [{ notification_id: 'mock-uuid' }] };
        }
        // Mock notification_planned insert
        if (sql.includes('INSERT INTO notification_planned')) {
          return { rowCount: 1, rows: [] };
        }
        return { rows: [], rowCount: 0 };
      }),
      release: vi.fn(),
    };
    return { client: client as any, executedQueries };
  }

  it('plans ALERT and ESCALATION rows for a fresh CRITICAL alert', async () => {
    const { client, executedQueries } = createMockClient();

    const created = await planOne(client, testConfig, defaultDeps, criticalAlert);
    expect(created).toBe(2); // 1 main ALERT + 1 ESCALATION

    const inserts = executedQueries.filter(q => q.sql.includes('INSERT INTO notifications'));
    expect(inserts).toHaveLength(2);

    // Verify main ALERT row
    const mainAlert = inserts.find(q => q.values[1] === 'ALERT');
    expect(mainAlert).toBeDefined();
    expect(mainAlert!.values[0]).toBe('alt-101');
    expect(mainAlert!.values[3]).toBe('control@example.org');
    expect(mainAlert!.values[6]).toBe('PENDING');

    // Verify ESCALATION row
    const escAlert = inserts.find(q => q.values[1] === 'ESCALATION');
    expect(escAlert).toBeDefined();
    expect(escAlert!.values[3]).toBe('duty@example.org');
    expect(escAlert!.values[9]).toBe(300); // due_at interval 300s

    // Verify notification_planned marker
    const marker = executedQueries.find(q => q.sql.includes('INSERT INTO notification_planned'));
    expect(marker).toBeDefined();
    expect(marker!.values[0]).toBe('alt-101');
    expect(marker!.values[1]).toBe('ROUTED');
  });

  it('marks row as SKIPPED when recipient domain is disallowed', async () => {
    const cfgDisallowed: NotificationConfig = {
      ...testConfig,
      routes: [
        {
          ...testConfig.routes[0]!,
          recipients: ['disallowed@external.com'],
          escalate: undefined,
        },
      ],
    };
    const { client, executedQueries } = createMockClient();

    const count = await planOne(client, cfgDisallowed, defaultDeps, criticalAlert);
    expect(count).toBe(1);

    const insert = executedQueries.find(q => q.sql.includes('INSERT INTO notifications'));
    expect(insert!.values[6]).toBe('SKIPPED');
    expect(insert!.values[7]).toBe('domain_not_allowed');
  });

  it('marks row as DRY_RUN when dryRun dependency is enabled', async () => {
    const dryRunDeps: PlannerDeps = {
      ...defaultDeps,
      dryRun: true,
    };
    const { client, executedQueries } = createMockClient();

    await planOne(client, testConfig, dryRunDeps, criticalAlert);

    const inserts = executedQueries.filter(q => q.sql.includes('INSERT INTO notifications'));
    expect(inserts.every(i => i.values[6] === 'DRY_RUN')).toBe(true);
  });

  it('records NO_ROUTE in planned marker when alert has no matching route', async () => {
    const lowAlert: AlertCtx = {
      ...criticalAlert,
      priority: 'LOW',
    };
    const { client, executedQueries } = createMockClient();

    const count = await planOne(client, testConfig, defaultDeps, lowAlert);
    expect(count).toBe(0);

    const marker = executedQueries.find(q => q.sql.includes('INSERT INTO notification_planned'));
    expect(marker).toBeDefined();
    expect(marker!.values[1]).toBe('NO_ROUTE');
    expect(marker!.values[2]).toBe(0);
  });
});
