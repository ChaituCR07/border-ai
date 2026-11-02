import { describe, expect, it, vi } from 'vitest';
import { PgAlertsRepo } from '../../src/modules/alerts/repo.pg.js';
import {
  NotificationWorker,
  type NotificationRow,
} from '../../src/modules/notifications/worker.js';
import { type NotificationConfig } from '../../src/modules/notifications/config.js';

describe('Escalation Cancellation on Acknowledge (Invariant I5)', () => {
  const dummyConfig: NotificationConfig = {
    version: 1,
    from: 'alerts@border-ai.local',
    base_url: 'http://localhost:5173',
    display_timezone: 'UTC',
    catchup_max_age_s: 3600,
    cooldown_s: 300,
    rate_limit: { per_recipient_per_min: 6 },
    max_attempts: 3,
    routes: [
      {
        name: 'critical-main',
        match: { priority: ['CRITICAL'] },
        recipients: ['control@example.org'],
        mode: 'immediate',
        include: { plate: true, snapshot: false, journey: false, explanation: true },
        escalate: { after_s: 300, recipients: ['duty@example.org'] },
      },
    ],
  };

  it('cancels pending escalation in the same transaction as acknowledge in PgAlertsRepo', async () => {
    const executedQueries: Array<{ sql: string; values?: any[] }> = [];

    const mockClient = {
      query: vi.fn(async (sql: string, values: any[] = []) => {
        executedQueries.push({ sql, values });
        if (sql.includes('UPDATE alerts')) {
          return { rowCount: 1, rows: [{ alert_id: 'alt-123' }] };
        }
        if (sql.includes('UPDATE notifications')) {
          return { rowCount: 1 };
        }
        return { rows: [], rowCount: 0 };
      }),
      release: vi.fn(),
    };

    const mockPool = {
      connect: vi.fn(async () => mockClient),
      query: vi.fn(async (sql: string, values: any[] = []) => {
        executedQueries.push({ sql, values });
        return {
          rows: [
            {
              alert_id: 'alt-123',
              event_id: 'ev-1',
              camera_id: 'CAM-01',
              priority: 'CRITICAL',
              status: 'ACKNOWLEDGED',
              acknowledged_by: 'op-1',
              acknowledged_at: new Date().toISOString(),
              created_at: new Date().toISOString(),
              event_type: 'ZONE_INTRUSION',
              threat_score: 90,
              snapshot_path: null,
              plate: 'KA01AB1234',
            },
          ],
        };
      }),
    };

    const repo = new PgAlertsRepo(mockPool as any);
    const result = await repo.acknowledge('alt-123', 'op-1');

    expect(result).not.toBeNull();
    expect(result!.updated).toBe(true);

    // Verify cancellation SQL was run inside transaction
    const cancelQuery = executedQueries.find(q =>
      q.sql.includes('UPDATE notifications') &&
      q.sql.includes("status = 'CANCELLED'") &&
      q.sql.includes("skip_reason = 'acknowledged'")
    );
    expect(cancelQuery).toBeDefined();
    expect(cancelQuery!.values).toContain('alt-123');

    // Verify COMMIT was called
    const commitQuery = executedQueries.find(q => q.sql === 'COMMIT');
    expect(commitQuery).toBeDefined();
  });

  it('worker pre-send check cancels escalation when claimed right after acknowledge (race guard)', async () => {
    const executedQueries: Array<{ sql: string; values?: any[] }> = [];

    const mockPool = {
      query: vi.fn(async (sql: string, values: any[] = []) => {
        executedQueries.push({ sql, values });
        // Alert status is already ACKNOWLEDGED in database
        if (sql.includes('SELECT status FROM alerts')) {
          return { rows: [{ status: 'ACKNOWLEDGED' }] };
        }
        return { rows: [], rowCount: 1 };
      }),
    };

    const mockTransport = {
      sendMail: vi.fn(),
    };

    const worker = new NotificationWorker(mockPool as any, dummyConfig, {
      allowedDomains: ['example.org'],
      dryRun: false,
      enabled: true,
      smtpTransport: mockTransport as any,
    });

    const escalationRow: NotificationRow = {
      notification_id: 'notif-race-1',
      alert_id: 'alt-123',
      kind: 'ESCALATION',
      channel: 'email',
      route_name: 'critical-main',
      recipient: 'duty@example.org',
      priority: 'CRITICAL',
      group_key: 'CAM-01|plate:KA01AB1234',
      status: 'SENDING',
      skip_reason: null,
      dedupe_key: 'alt-123|ESCALATION|critical-main|duty@example.org',
      due_at: '2026-11-02T12:05:00Z',
      next_attempt_at: '2026-11-02T12:05:00Z',
      attempts: 1,
      locked_until: '2026-11-02T12:06:00Z',
      last_error: null,
      message_id: null,
      sent_at: null,
      created_at: '2026-11-02T12:00:00Z',
    };

    await worker.processRow(escalationRow);

    // Verify email was not sent
    expect(mockTransport.sendMail).not.toHaveBeenCalled();

    // Verify row was cancelled
    const cancelQuery = executedQueries.find(q =>
      q.sql.includes('UPDATE notifications') &&
      q.sql.includes("status = 'CANCELLED'") &&
      q.sql.includes("skip_reason = 'acknowledged'")
    );
    expect(cancelQuery).toBeDefined();
    expect(worker.metrics.cancelledTotal).toBe(1);
  });
});
