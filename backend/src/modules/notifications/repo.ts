import type pg from 'pg';
import { type Priority } from './config.js';
import { type Cursor } from '../../common/pagination.js';

export interface NotificationLogItem {
  notification_id: string;
  alert_id: string;
  kind: string;
  channel: string;
  route_name: string;
  recipient: string;
  priority: Priority;
  group_key: string | null;
  status: string;
  skip_reason: string | null;
  attempts: number;
  last_error: string | null;
  message_id: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface NotificationFilters {
  alertId?: string;
  status?: string;
  kind?: string;
}

export interface QueueStats {
  pending: number;
  sending: number;
  failed: number;
  sent_24h: number;
  skipped_24h: number;
  oldest_pending_age_s: number | null;
  stale_alerts_24h: number;
}

export function maskRecipient(email: string): string {
  const parts = email.split('@');
  if (parts.length !== 2) return '***';
  const [user, domain] = parts;
  if (!user || !domain) return '***';
  if (user.length <= 2) return `***@${domain}`;
  return `${user[0]}***${user[user.length - 1]}@${domain}`;
}

export class NotificationsRepo {
  constructor(private pool: pg.Pool) {}

  async list(
    filters: NotificationFilters,
    limit: number,
    cursor?: Cursor
  ): Promise<NotificationLogItem[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (filters.alertId) {
      where.push(`alert_id = $${idx++}`);
      args.push(filters.alertId);
    }
    if (filters.status) {
      where.push(`status = $${idx++}`);
      args.push(filters.status);
    }
    if (filters.kind) {
      where.push(`kind = $${idx++}`);
      args.push(filters.kind);
    }
    if (cursor) {
      where.push(`(created_at, notification_id) < ($${idx++}, $${idx++})`);
      args.push(cursor.t, cursor.id);
    }

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    const sql = `
      SELECT notification_id, alert_id, kind, channel, route_name, recipient,
             priority, group_key, status, skip_reason, attempts, last_error,
             message_id, sent_at, created_at
        FROM notifications
       ${whereClause}
       ORDER BY created_at DESC, notification_id DESC
       LIMIT $${idx}
    `;
    args.push(limit);

    const { rows } = await this.pool.query(sql, args);
    return rows.map((r: any) => ({
      ...r,
      created_at: new Date(r.created_at).toISOString(),
      sent_at: r.sent_at ? new Date(r.sent_at).toISOString() : null,
    }));
  }

  async getQueueStats(): Promise<QueueStats> {
    const sql = `
      SELECT
        COUNT(*) FILTER (WHERE status = 'PENDING') AS pending,
        COUNT(*) FILTER (WHERE status = 'SENDING') AS sending,
        COUNT(*) FILTER (WHERE status = 'FAILED') AS failed,
        COUNT(*) FILTER (WHERE status = 'SENT' AND sent_at >= now() - interval '24 hours') AS sent_24h,
        COUNT(*) FILTER (WHERE status = 'SKIPPED' AND created_at >= now() - interval '24 hours') AS skipped_24h,
        EXTRACT(EPOCH FROM (now() - MIN(created_at))) FILTER (WHERE status = 'PENDING') AS oldest_pending_age_s
      FROM notifications;
    `;
    const { rows } = await this.pool.query(sql);
    const r = rows[0] || {};

    const staleSql = `
      SELECT COUNT(*) AS count
        FROM notification_planned
       WHERE outcome = 'STALE'
         AND planned_at >= now() - interval '24 hours';
    `;
    const { rows: staleRows } = await this.pool.query(staleSql);

    return {
      pending: Number(r.pending || 0),
      sending: Number(r.sending || 0),
      failed: Number(r.failed || 0),
      sent_24h: Number(r.sent_24h || 0),
      skipped_24h: Number(r.skipped_24h || 0),
      oldest_pending_age_s: r.oldest_pending_age_s ? Math.round(Number(r.oldest_pending_age_s)) : null,
      stale_alerts_24h: Number(staleRows[0]?.count || 0),
    };
  }

  async retry(notificationId: string): Promise<boolean> {
    const { rowCount } = await this.pool.query(
      `UPDATE notifications
          SET status = 'PENDING',
              attempts = 0,
              next_attempt_at = now(),
              locked_until = NULL,
              last_error = NULL
        WHERE notification_id = $1::uuid AND status = 'FAILED'`,
      [notificationId]
    );
    return (rowCount ?? 0) > 0;
  }

  async enqueueTest(recipient: string): Promise<string> {
    const { rows } = await this.pool.query(
      `INSERT INTO notifications (
        alert_id, kind, channel, route_name, recipient, priority, status, dedupe_key
      )
      VALUES (
        '00000000-0000-0000-0000-000000000000', 'TEST', 'email', 'test-route', $1, 'LOW', 'PENDING',
        'TEST|' || gen_random_uuid()
      )
      RETURNING notification_id`,
      [recipient]
    );
    return rows[0]!.notification_id;
  }
}
