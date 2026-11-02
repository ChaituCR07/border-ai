import pg from 'pg';
import nodemailer, { type Transporter } from 'nodemailer';
import { type NotificationConfig, type Priority } from './config.js';
import {
  type EmailModel,
  buildDeepLinks,
  renderEmail,
  renderTestEmail,
} from './rendering.js';
import { sanitizeHeader, backoffDelay, domainAllowed } from './policy.js';
import { processSnapshot } from './snapshot.js';
import { buildJourneySummary, type JourneyDeps } from './journey.js';

export interface NotificationRow {
  notification_id: string;
  alert_id: string;
  kind: 'ALERT' | 'ESCALATION' | 'DIGEST' | 'TEST';
  channel: string;
  route_name: string;
  recipient: string;
  priority: Priority;
  group_key: string | null;
  status: 'PENDING' | 'SENDING' | 'SENT' | 'FAILED' | 'CANCELLED' | 'SKIPPED' | 'DRY_RUN';
  skip_reason: string | null;
  dedupe_key: string;
  due_at: string;
  next_attempt_at: string;
  attempts: number;
  locked_until: string | null;
  last_error: string | null;
  message_id: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface WorkerDeps {
  allowedDomains: string[];
  dryRun: boolean;
  enabled: boolean;
  smtpTransport?: Transporter;
  journeyDeps?: JourneyDeps;
}

export interface WorkerMetrics {
  sentTotal: number;
  failedTotal: number;
  skippedTotal: number;
  deferredTotal: number;
  cancelledTotal: number;
}

export class SlidingWindowRateLimiter {
  private windowMs = 60 * 1000;
  private sends: Map<string, number[]> = new Map();

  constructor(private maxPerMin: number) {}

  canSend(recipient: string, nowMs = Date.now()): boolean {
    const cutoff = nowMs - this.windowMs;
    const history = (this.sends.get(recipient) || []).filter(t => t > cutoff);
    this.sends.set(recipient, history);
    return history.length < this.maxPerMin;
  }

  recordSend(recipient: string, nowMs = Date.now()): void {
    const history = this.sends.get(recipient) || [];
    history.push(nowMs);
    this.sends.set(recipient, history);
  }
}

export class NotificationWorker {
  private running = false;
  private timer: NodeJS.Timeout | null = null;
  private inFlight = new Set<string>();
  private transport: Transporter;
  private rateLimiter: SlidingWindowRateLimiter;
  public metrics: WorkerMetrics = {
    sentTotal: 0,
    failedTotal: 0,
    skippedTotal: 0,
    deferredTotal: 0,
    cancelledTotal: 0,
  };

  constructor(
    private pool: pg.Pool,
    private config: NotificationConfig,
    private deps: WorkerDeps,
    private intervalMs = 1500,
    private concurrency = 2
  ) {
    this.rateLimiter = new SlidingWindowRateLimiter(
      config.rate_limit.per_recipient_per_min || 6
    );

    if (deps.smtpTransport) {
      this.transport = deps.smtpTransport;
    } else {
      const host = process.env.SMTP_HOST || 'localhost';
      const port = Number(process.env.SMTP_PORT || 1025);
      const user = process.env.SMTP_USER || undefined;
      const pass = process.env.SMTP_PASS || undefined;
      const requireTls = process.env.SMTP_REQUIRE_TLS === 'true';

      this.transport = nodemailer.createTransport({
        host,
        port,
        secure: false,
        requireTLS: requireTls,
        auth: user ? { user, pass } : undefined,
        pool: true,
        maxConnections: 2,
        connectionTimeout: 10_000,
        socketTimeout: 15_000,
        tls: { rejectUnauthorized: process.env.NODE_ENV === 'production' },
      });
    }
  }

  async start(): Promise<void> {
    if (this.running) return;
    this.running = true;

    this.timer = setInterval(() => {
      this.tick().catch(err => {
        console.error('[worker] Error during worker tick:', err);
      });
    }, this.intervalMs);
  }

  async stop(): Promise<void> {
    this.running = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }

    // Wait for in-flight sends to finish up to 5s
    const startWait = Date.now();
    while (this.inFlight.size > 0 && Date.now() - startWait < 5000) {
      await new Promise(r => setTimeout(r, 100));
    }
  }

  async claimRows(limit: number): Promise<NotificationRow[]> {
    const query = `
      UPDATE notifications n
         SET status = 'SENDING',
             locked_until = now() + interval '60 seconds',
             attempts = n.attempts + 1
       WHERE n.notification_id IN (
         SELECT notification_id FROM notifications
          WHERE kind IN ('ALERT', 'ESCALATION', 'TEST')
            AND (
              (status = 'PENDING' AND next_attempt_at <= now() AND due_at <= now())
              OR (status = 'SENDING' AND locked_until < now())
            )
          ORDER BY due_at, created_at
          FOR UPDATE SKIP LOCKED
          LIMIT $1
       )
       RETURNING *;
    `;
    const { rows } = await this.pool.query(query, [limit]);
    return rows;
  }

  async processRow(row: NotificationRow): Promise<void> {
    const id = row.notification_id;
    this.inFlight.add(id);

    try {
      // 1. Kill-switch check
      if (!this.deps.enabled) {
        await this.pool.query(
          `UPDATE notifications SET status = 'PENDING', attempts = attempts - 1, locked_until = NULL WHERE notification_id = $1`,
          [id]
        );
        return;
      }

      // 2. Pre-send check: ESCALATION cancelled if alert is no longer OPEN
      if (row.kind === 'ESCALATION') {
        const { rows: alertRows } = await this.pool.query(
          `SELECT status FROM alerts WHERE alert_id = $1`,
          [row.alert_id]
        );
        if (alertRows.length > 0 && alertRows[0].status !== 'OPEN') {
          await this.pool.query(
            `UPDATE notifications SET status = 'CANCELLED', skip_reason = 'acknowledged', locked_until = NULL WHERE notification_id = $1`,
            [id]
          );
          this.metrics.cancelledTotal++;
          return;
        }
      }

      // 3. Domain allow-list check
      if (!domainAllowed(row.recipient, this.deps.allowedDomains)) {
        await this.pool.query(
          `UPDATE notifications SET status = 'SKIPPED', skip_reason = 'domain_not_allowed', locked_until = NULL WHERE notification_id = $1`,
          [id]
        );
        this.metrics.skippedTotal++;
        return;
      }

      // 4. Rate-limit check (defer without counting as attempt)
      if (!this.rateLimiter.canSend(row.recipient)) {
        await this.pool.query(
          `UPDATE notifications
              SET status = 'PENDING',
                  attempts = attempts - 1,
                  next_attempt_at = now() + interval '30 seconds',
                  locked_until = NULL
            WHERE notification_id = $1`,
          [id]
        );
        this.metrics.deferredTotal++;
        return;
      }

      // 5. Test email kind
      if (row.kind === 'TEST') {
        const mail = renderTestEmail(row.recipient);
        const info = await this.transport.sendMail({
          from: this.config.from,
          to: row.recipient,
          subject: sanitizeHeader(mail.subject),
          text: mail.text,
          html: mail.html,
          messageId: `<${id}@border-ai.local>`,
        });

        await this.pool.query(
          `UPDATE notifications SET status = 'SENT', sent_at = now(), message_id = $2, locked_until = NULL, last_error = NULL WHERE notification_id = $1`,
          [id, info.messageId]
        );
        this.rateLimiter.recordSend(row.recipient);
        this.metrics.sentTotal++;
        return;
      }

      // 6. Fetch full alert & event detail for model assembly
      const { rows: details } = await this.pool.query(
        `SELECT a.alert_id, a.priority, a.created_at, a.threat_score,
                e.camera_id, e.event_type, e.plate_norm AS plate, e.snapshot_path,
                e.metadata, e.object_class,
                c.location_label AS camera_name
           FROM alerts a
           JOIN events e ON e.event_id = a.event_id
           LEFT JOIN cameras c ON c.camera_id = e.camera_id
          WHERE a.alert_id = $1`,
        [row.alert_id]
      );

      if (details.length === 0) {
        throw new Error(`Alert details not found for alert_id ${row.alert_id}`);
      }

      const alertInfo = details[0]!;
      const meta = typeof alertInfo.metadata === 'string' ? JSON.parse(alertInfo.metadata) : alertInfo.metadata || {};
      const isPerson =
        alertInfo.object_class === 'person' ||
        ['FACE_MATCH', 'REID_CANDIDATE', 'WATCHLIST_PERSON'].includes(alertInfo.event_type) ||
        meta.person_related === true;

      // Find route configuration
      const route = this.config.routes.find(r => r.name === row.route_name) || {
        name: row.route_name,
        match: { priority: [row.priority] },
        recipients: [row.recipient],
        mode: 'immediate' as const,
        include: { plate: true, snapshot: true, journey: true, explanation: true },
      };

      // Best effort snapshot (with person-related privacy gate)
      const snapshot = route.include.snapshot
        ? await processSnapshot(alertInfo.snapshot_path, { personRelated: isPerson })
        : null;

      // Best effort journey
      let journeySummary = null;
      if (route.include.journey && alertInfo.plate && this.deps.journeyDeps) {
        journeySummary = await buildJourneySummary(
          alertInfo.plate,
          alertInfo.camera_id,
          new Date(alertInfo.created_at).toISOString(),
          this.deps.journeyDeps
        );
      }

      // Parse explanation
      const factors = meta.explanation?.factors || meta.contributions || [];
      const explanation = factors.map((f: any) => ({
        name: f.name || f.label || 'Detection factor',
        points: Number(f.points) || 0,
        detail: f.detail || (Array.isArray(f.reasons) ? f.reasons.join(', ') : undefined),
      }));

      const deepLinks = buildDeepLinks(
        this.config.base_url,
        alertInfo.alert_id,
        alertInfo.plate,
        new Date(alertInfo.created_at).toISOString()
      );

      const emailModel: EmailModel = {
        alert: {
          alert_id: alertInfo.alert_id,
          priority: alertInfo.priority,
          created_at: new Date(alertInfo.created_at).toISOString(),
          threat_score: alertInfo.threat_score,
          camera_id: alertInfo.camera_id,
          camera_name: alertInfo.camera_name || undefined,
          event_type: alertInfo.event_type,
          summary: meta.summary || alertInfo.event_type,
          plate: alertInfo.plate,
          person_related: isPerson,
        },
        explanation,
        journey: journeySummary,
        snapshot,
        links: deepLinks,
        tz: this.config.display_timezone || 'UTC',
        include: route.include,
        escalation_after_min: route.escalate ? Math.round(route.escalate.after_s / 60) : 5,
        kind: row.kind,
      };

      const mail = renderEmail(emailModel);

      // Handle dry-run mode
      if (this.deps.dryRun) {
        await this.pool.query(
          `UPDATE notifications SET status = 'DRY_RUN', sent_at = now(), locked_until = NULL, last_error = NULL WHERE notification_id = $1`,
          [id]
        );
        this.metrics.sentTotal++;
        return;
      }

      // Send mail through SMTP transport
      const headers: Record<string, string> = {
        'Auto-Submitted': 'auto-generated',
        'X-Border-AI-Alert-Id': sanitizeHeader(row.alert_id),
        'X-Border-AI-Priority': row.priority,
      };
      if (row.priority === 'CRITICAL') {
        headers['X-Priority'] = '1';
        headers['Importance'] = 'high';
      }

      const info = await this.transport.sendMail({
        from: this.config.from,
        to: row.recipient,
        subject: sanitizeHeader(mail.subject),
        text: mail.text,
        html: mail.html,
        attachments: mail.attachments.map(att => ({
          filename: att.filename,
          content: att.content,
          cid: att.cid,
          contentType: att.contentType,
        })),
        messageId: `<${id}@border-ai.local>`,
        headers,
      });

      await this.pool.query(
        `UPDATE notifications SET status = 'SENT', sent_at = now(), message_id = $2, locked_until = NULL, last_error = NULL WHERE notification_id = $1`,
        [id, info.messageId]
      );
      this.rateLimiter.recordSend(row.recipient);
      this.metrics.sentTotal++;
    } catch (err: any) {
      const delayS = backoffDelay(row.attempts);
      const isFailed = row.attempts >= this.config.max_attempts;
      const nextStatus = isFailed ? 'FAILED' : 'PENDING';

      await this.pool.query(
        `UPDATE notifications
            SET status = $2,
                next_attempt_at = now() + make_interval(secs => $3),
                last_error = left($4, 500),
                locked_until = NULL
          WHERE notification_id = $1`,
        [id, nextStatus, delayS, String(err.message || err)]
      );

      if (isFailed) {
        this.metrics.failedTotal++;
      }
    } finally {
      this.inFlight.delete(id);
    }
  }

  async tick(): Promise<number> {
    if (!this.running) return 0;

    const availableSlots = this.concurrency - this.inFlight.size;
    if (availableSlots <= 0) return 0;

    try {
      const rows = await this.claimRows(availableSlots);
      for (const row of rows) {
        this.processRow(row).catch(err => {
          console.error(`[worker] Error processing notification ${row.notification_id}:`, err);
        });
      }
      return rows.length;
    } catch (err) {
      console.error('[worker] Error claiming notifications:', err);
      return 0;
    }
  }
}
