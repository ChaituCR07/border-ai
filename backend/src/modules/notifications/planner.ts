import pg from 'pg';
import {
  type NotificationConfig,
  type Priority,
  type Route,
} from './config.js';
import {
  type AlertCtx,
  type LastInGroup,
  matchRoutes,
  groupKey,
  decide,
  domainAllowed,
} from './policy.js';

export interface PlannerDeps {
  allowedDomains: string[];
  dryRun: boolean;
  enabled: boolean;
}

export const PLANNER_ADVISORY_LOCK_ID = 727001;

function toCtx(row: any): AlertCtx {
  const metadata = typeof row.metadata === 'string' ? JSON.parse(row.metadata) : row.metadata || {};
  const isPerson =
    row.object_class === 'person' ||
    ['FACE_MATCH', 'REID_CANDIDATE', 'WATCHLIST_PERSON'].includes(row.event_type) ||
    metadata.person_related === true;

  return {
    alert_id: row.alert_id,
    priority: row.priority as Priority,
    created_at: new Date(row.created_at).toISOString(),
    camera_id: row.camera_id,
    event_type: row.event_type,
    plate: row.plate || null,
    person_related: isPerson,
  };
}

async function lastInGroup(
  client: pg.PoolClient,
  routeName: string,
  key: string
): Promise<LastInGroup | null> {
  const { rows } = await client.query(
    `SELECT priority,
            EXTRACT(EPOCH FROM (now() - created_at))::float AS created_at_age_s
       FROM notifications
      WHERE route_name = $1
        AND group_key = $2
        AND status IN ('SENT', 'PENDING', 'SENDING')
      ORDER BY created_at DESC
      LIMIT 1`,
    [routeName, key]
  );
  if (rows.length === 0) return null;
  return {
    priority: rows[0].priority as Priority,
    created_at_age_s: Math.max(0, rows[0].created_at_age_s),
  };
}

interface InsertNotificationParam {
  alert_id: string;
  kind: 'ALERT' | 'ESCALATION' | 'DIGEST' | 'TEST';
  route: Route;
  recipient: string;
  priority: Priority;
  group_key: string;
  status: 'PENDING' | 'SENDING' | 'SENT' | 'FAILED' | 'CANCELLED' | 'SKIPPED' | 'DRY_RUN';
  skip_reason: string | null;
  due_at_interval_s: number;
}

async function insertNotification(
  client: pg.PoolClient,
  p: InsertNotificationParam
): Promise<number> {
  const dedupeKey = `${p.alert_id}|${p.kind}|${p.route.name}|${p.recipient}`;

  const query = `
    INSERT INTO notifications (
      alert_id, kind, channel, route_name, recipient, priority, group_key,
      status, skip_reason, dedupe_key, due_at, next_attempt_at
    )
    VALUES (
      $1, $2, 'email', $3, $4, $5, $6,
      $7, $8, $9, now() + make_interval(secs => $10), now() + make_interval(secs => $10)
    )
    ON CONFLICT (dedupe_key) DO NOTHING
    RETURNING notification_id
  `;

  const { rowCount } = await client.query(query, [
    p.alert_id,
    p.kind,
    p.route.name,
    p.recipient,
    p.priority,
    p.group_key,
    p.status,
    p.skip_reason,
    dedupeKey,
    p.due_at_interval_s,
  ]);

  return rowCount ?? 0;
}

export async function planOne(
  client: pg.PoolClient,
  cfg: NotificationConfig,
  deps: PlannerDeps,
  a: AlertCtx
): Promise<number> {
  const routes = matchRoutes(cfg, a);
  let created = 0;
  const gk = groupKey(a);

  for (const route of routes) {
    for (const rcpt of route.recipients) {
      const last = route.mode === 'immediate' ? await lastInGroup(client, route.name, gk) : null;
      const d = decide(route, a, last, cfg.cooldown_s);
      const allowed = domainAllowed(rcpt, deps.allowedDomains);

      let status: 'PENDING' | 'SKIPPED' | 'DRY_RUN' = 'PENDING';
      let reason: string | null = null;

      if (!deps.enabled) {
        status = 'SKIPPED';
        reason = 'notifications_disabled';
      } else if (!allowed) {
        status = 'SKIPPED';
        reason = 'domain_not_allowed';
      } else if (d.action === 'SKIP') {
        status = 'SKIPPED';
        reason = d.reason;
      } else if (deps.dryRun) {
        status = 'DRY_RUN';
      }

      const inserted = await insertNotification(client, {
        alert_id: a.alert_id,
        kind: route.mode === 'digest' ? 'DIGEST' : 'ALERT',
        route,
        recipient: rcpt,
        priority: a.priority,
        group_key: gk,
        status,
        skip_reason: reason,
        due_at_interval_s: 0,
      });
      created += inserted;

      // Plan escalation for unacknowledged CRITICAL alerts if route specifies escalation
      if (route.escalate && status === 'PENDING' && a.priority === 'CRITICAL') {
        for (const er of route.escalate.recipients) {
          const escAllowed = domainAllowed(er, deps.allowedDomains);
          const escStatus = !deps.enabled
            ? 'SKIPPED'
            : !escAllowed
            ? 'SKIPPED'
            : deps.dryRun
            ? 'DRY_RUN'
            : 'PENDING';
          const escReason = !escAllowed ? 'domain_not_allowed' : null;

          const escInserted = await insertNotification(client, {
            alert_id: a.alert_id,
            kind: 'ESCALATION',
            route,
            recipient: er,
            priority: a.priority,
            group_key: gk,
            status: escStatus,
            skip_reason: escReason,
            due_at_interval_s: route.escalate.after_s,
          });
          created += escInserted;
        }
      }
    }
  }

  const outcome = routes.length > 0 ? 'ROUTED' : 'NO_ROUTE';
  await client.query(
    `INSERT INTO notification_planned (alert_id, outcome, routes)
     VALUES ($1, $2, $3)
     ON CONFLICT DO NOTHING`,
    [a.alert_id, outcome, created]
  );

  return created;
}

export async function markStale(db: pg.Pool, cfg: NotificationConfig): Promise<number> {
  const { rowCount } = await db.query(
    `INSERT INTO notification_planned (alert_id, outcome, routes)
     SELECT a.alert_id, 'STALE', 0
       FROM alerts a
      WHERE NOT EXISTS (SELECT 1 FROM notification_planned p WHERE p.alert_id = a.alert_id)
        AND a.created_at < now() - make_interval(secs => $1)
      ON CONFLICT DO NOTHING`,
    [cfg.catchup_max_age_s]
  );
  return rowCount ?? 0;
}

export async function planBatch(
  db: pg.Pool,
  cfg: NotificationConfig,
  deps: PlannerDeps,
  limit = 100
): Promise<{ planned: number; totalAlerts: number }> {
  const { rows } = await db.query(
    `SELECT a.alert_id, a.priority, a.created_at, a.status,
            e.camera_id, e.event_type, e.plate_norm AS plate, e.metadata, e.object_class
       FROM alerts a
       JOIN events e ON e.event_id = a.event_id
      WHERE NOT EXISTS (SELECT 1 FROM notification_planned p WHERE p.alert_id = a.alert_id)
        AND a.created_at >= now() - make_interval(secs => $1)
        AND a.status = 'OPEN'
      ORDER BY a.created_at, a.alert_id
      LIMIT $2`,
    [cfg.catchup_max_age_s, limit]
  );

  let plannedTotal = 0;
  for (const r of rows) {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const ctx = toCtx(r);
      const count = await planOne(client, cfg, deps, ctx);
      await client.query('COMMIT');
      plannedTotal += count;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  await markStale(db, cfg);
  return { planned: plannedTotal, totalAlerts: rows.length };
}

export class NotificationPlanner {
  private running = false;
  private timer: NodeJS.Timeout | null = null;
  private lockClient: pg.PoolClient | null = null;
  private isStandby = false;

  constructor(
    private pool: pg.Pool,
    private config: NotificationConfig,
    private deps: PlannerDeps,
    private intervalMs = 1500
  ) {}

  async start(): Promise<void> {
    if (this.running) return;
    this.running = true;

    // Acquire PostgreSQL session advisory lock to ensure single active planner
    await this.tryAcquireLock();

    this.timer = setInterval(() => {
      this.tick().catch(err => {
        console.error('[planner] Unhandled error during planner tick:', err);
      });
    }, this.intervalMs);
  }

  async kick(): Promise<void> {
    if (!this.running || this.isStandby) return;
    try {
      await this.tick();
    } catch (err) {
      console.warn('[planner] Error during kicked tick:', err);
    }
  }

  private async tryAcquireLock(): Promise<boolean> {
    try {
      this.lockClient = await this.pool.connect();
      const { rows } = await this.lockClient.query(
        'SELECT pg_try_advisory_lock($1) AS ok',
        [PLANNER_ADVISORY_LOCK_ID]
      );
      if (rows[0]?.ok) {
        this.isStandby = false;
        return true;
      }
      this.isStandby = true;
      this.lockClient.release();
      this.lockClient = null;
      return false;
    } catch (err) {
      this.isStandby = true;
      if (this.lockClient) {
        this.lockClient.release();
        this.lockClient = null;
      }
      return false;
    }
  }

  async tick(): Promise<number> {
    if (this.isStandby) {
      const got = await this.tryAcquireLock();
      if (!got) return 0;
    }

    try {
      const { planned } = await planBatch(this.pool, this.config, this.deps);
      return planned;
    } catch (err) {
      console.error('[planner] Error during planBatch:', err);
      return 0;
    }
  }

  async stop(): Promise<void> {
    this.running = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (this.lockClient) {
      try {
        await this.lockClient.query('SELECT pg_advisory_unlock($1)', [PLANNER_ADVISORY_LOCK_ID]);
      } catch {
        // connection close will auto-release lock anyway
      } finally {
        this.lockClient.release();
        this.lockClient = null;
      }
    }
  }

  getStatus() {
    return {
      running: this.running,
      isStandby: this.isStandby,
      active: this.running && !this.isStandby,
    };
  }
}
