import { describe, expect, it, vi, beforeEach } from 'vitest';
import {
  NotificationWorker,
  SlidingWindowRateLimiter,
  type NotificationRow,
} from '../../src/modules/notifications/worker.js';
import { type NotificationConfig } from '../../src/modules/notifications/config.js';

describe('Notification Sender Worker Unit Tests', () => {
  describe('SlidingWindowRateLimiter', () => {
    it('allows sends within limit and defers excess', () => {
      const limiter = new SlidingWindowRateLimiter(3);
      const recipient = 'user@example.org';
      const now = 1000000;

      expect(limiter.canSend(recipient, now)).toBe(true);
      limiter.recordSend(recipient, now);

      expect(limiter.canSend(recipient, now + 1000)).toBe(true);
      limiter.recordSend(recipient, now + 1000);

      expect(limiter.canSend(recipient, now + 2000)).toBe(true);
      limiter.recordSend(recipient, now + 2000);

      // 4th send within the minute is deferred
      expect(limiter.canSend(recipient, now + 3000)).toBe(false);

      // After 61 seconds, window expires and send is allowed again
      expect(limiter.canSend(recipient, now + 61000)).toBe(true);
    });
  });

  describe('Worker Processing Logic (Mock Pool & Transport)', () => {
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
          name: 'critical-route',
          match: { priority: ['CRITICAL'] },
          recipients: ['duty@example.org'],
          mode: 'immediate',
          include: { plate: true, snapshot: false, journey: false, explanation: true },
        },
      ],
    };

    let mockPool: any;
    let mockTransport: any;
    let executedQueries: Array<{ sql: string; values: any[] }>;

    beforeEach(() => {
      executedQueries = [];
      mockPool = {
        query: vi.fn(async (sql: string, values: any[] = []) => {
          executedQueries.push({ sql, values });
          // Mock alert details fetch
          if (sql.includes('FROM alerts a') && sql.includes('JOIN events e')) {
            return {
              rows: [
                {
                  alert_id: 'alt-1',
                  priority: 'CRITICAL',
                  created_at: '2026-11-02T12:00:00Z',
                  threat_score: 95,
                  camera_id: 'CAM-01',
                  event_type: 'ZONE_INTRUSION',
                  plate: 'KA01AB1234',
                  snapshot_path: null,
                  metadata: JSON.stringify({ summary: 'Zone breach' }),
                  object_class: 'car',
                  camera_name: 'Main Gate',
                },
              ],
            };
          }
          // Mock alert status check for escalation
          if (sql.includes('SELECT status FROM alerts WHERE alert_id')) {
            return { rows: [{ status: 'ACKNOWLEDGED' }] };
          }
          return { rows: [], rowCount: 1 };
        }),
      };

      mockTransport = {
        sendMail: vi.fn(async () => ({ messageId: '<msg-123@smtp>' })),
      };
    });

    it('cancels ESCALATION when alert is already ACKNOWLEDGED', async () => {
      const worker = new NotificationWorker(
        mockPool,
        dummyConfig,
        {
          allowedDomains: ['example.org'],
          dryRun: false,
          enabled: true,
          smtpTransport: mockTransport,
        }
      );

      const row: NotificationRow = {
        notification_id: 'notif-esc-1',
        alert_id: 'alt-1',
        kind: 'ESCALATION',
        channel: 'email',
        route_name: 'critical-route',
        recipient: 'duty@example.org',
        priority: 'CRITICAL',
        group_key: 'CAM-01|plate:KA01AB1234',
        status: 'SENDING',
        skip_reason: null,
        dedupe_key: 'alt-1|ESCALATION|critical-route|duty@example.org',
        due_at: '2026-11-02T12:05:00Z',
        next_attempt_at: '2026-11-02T12:05:00Z',
        attempts: 1,
        locked_until: '2026-11-02T12:06:00Z',
        last_error: null,
        message_id: null,
        sent_at: null,
        created_at: '2026-11-02T12:00:00Z',
      };

      await worker.processRow(row);

      expect(mockTransport.sendMail).not.toHaveBeenCalled();
      const cancelUpdate = executedQueries.find(q => q.sql.includes("status = 'CANCELLED'"));
      expect(cancelUpdate).toBeDefined();
      expect(cancelUpdate!.values[0]).toBe('notif-esc-1');
      expect(worker.metrics.cancelledTotal).toBe(1);
    });

    it('sends email and updates status to SENT on valid ALERT row', async () => {
      const worker = new NotificationWorker(
        mockPool,
        dummyConfig,
        {
          allowedDomains: ['example.org'],
          dryRun: false,
          enabled: true,
          smtpTransport: mockTransport,
        }
      );

      const row: NotificationRow = {
        notification_id: 'notif-alert-1',
        alert_id: 'alt-1',
        kind: 'ALERT',
        channel: 'email',
        route_name: 'critical-route',
        recipient: 'duty@example.org',
        priority: 'CRITICAL',
        group_key: 'CAM-01|plate:KA01AB1234',
        status: 'SENDING',
        skip_reason: null,
        dedupe_key: 'alt-1|ALERT|critical-route|duty@example.org',
        due_at: '2026-11-02T12:00:00Z',
        next_attempt_at: '2026-11-02T12:00:00Z',
        attempts: 1,
        locked_until: '2026-11-02T12:01:00Z',
        last_error: null,
        message_id: null,
        sent_at: null,
        created_at: '2026-11-02T12:00:00Z',
      };

      await worker.processRow(row);

      expect(mockTransport.sendMail).toHaveBeenCalledTimes(1);
      const sentUpdate = executedQueries.find(q => q.sql.includes("status = 'SENT'"));
      expect(sentUpdate).toBeDefined();
      expect(sentUpdate!.values[0]).toBe('notif-alert-1');
      expect(sentUpdate!.values[1]).toBe('<msg-123@smtp>');
      expect(worker.metrics.sentTotal).toBe(1);
    });

    it('handles SMTP transport failure and updates retry backoff', async () => {
      mockTransport.sendMail = vi.fn(async () => {
        throw new Error('SMTP connection reset');
      });

      const worker = new NotificationWorker(
        mockPool,
        dummyConfig,
        {
          allowedDomains: ['example.org'],
          dryRun: false,
          enabled: true,
          smtpTransport: mockTransport,
        }
      );

      const row: NotificationRow = {
        notification_id: 'notif-alert-1',
        alert_id: 'alt-1',
        kind: 'ALERT',
        channel: 'email',
        route_name: 'critical-route',
        recipient: 'duty@example.org',
        priority: 'CRITICAL',
        group_key: 'CAM-01|plate:KA01AB1234',
        status: 'SENDING',
        skip_reason: null,
        dedupe_key: 'alt-1|ALERT|critical-route|duty@example.org',
        due_at: '2026-11-02T12:00:00Z',
        next_attempt_at: '2026-11-02T12:00:00Z',
        attempts: 1,
        locked_until: '2026-11-02T12:01:00Z',
        last_error: null,
        message_id: null,
        sent_at: null,
        created_at: '2026-11-02T12:00:00Z',
      };

      await worker.processRow(row);

      const retryUpdate = executedQueries.find(q => q.sql.includes('next_attempt_at = now() + make_interval'));
      expect(retryUpdate).toBeDefined();
      expect(retryUpdate!.values[1]).toBe('PENDING'); // Retry scheduled
      expect(retryUpdate!.values[2]).toBe(10); // Attempt 1 backoff is 10s
    });
  });
});
