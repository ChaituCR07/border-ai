import type { AlertView } from '@border-ai/protocol';
import type { AlertEnvelope } from './envelope.js';
import type { AlertsRepo } from '../modules/alerts/repo.js';

export const WAITS_MS = [0, 50, 100, 200, 400, 800, 1500];

export class AlertHydrator {
  private recentIds = new Map<string, number>();

  constructor(
    private alertsRepo: AlertsRepo,
    private sleepFn: (ms: number) => Promise<void> = (ms) => new Promise((r) => setTimeout(r, ms))
  ) {}

  /**
   * Returns true if alert was already broadcast recently (within windowMs).
   */
  isDuplicate(alertId: string, windowMs = 60_000): boolean {
    const now = Date.now();
    this.cleanup(now, windowMs);

    if (this.recentIds.has(alertId)) {
      return true;
    }
    this.recentIds.set(alertId, now);
    return false;
  }

  private cleanup(now: number, windowMs: number): void {
    if (this.recentIds.size > 2000) {
      for (const [id, ts] of this.recentIds.entries()) {
        if (now - ts > windowMs) {
          this.recentIds.delete(id);
        }
      }
    }
  }

  async hydrate(env: AlertEnvelope): Promise<AlertView> {
    for (const waitMs of WAITS_MS) {
      if (waitMs > 0) {
        await this.sleepFn(waitMs);
      }

      try {
        const row = await this.alertsRepo.getById(env.alert_id);
        if (row) {
          return {
            alert_id: row.alert_id,
            event_id: row.event_id,
            priority: row.priority,
            status: row.status,
            acknowledged_by: row.acknowledged_by,
            acknowledged_at: row.acknowledged_at,
            created_at: row.created_at,
            persisted: true,
            event: {
              camera_id: row.event.camera_id,
              event_type: row.event.event_type,
              threat_score: row.event.threat_score,
              plate: row.event.plate ?? null,
              timestamp: row.created_at,
              snapshot_url: row.event.snapshot_url,
              snapshot_available: Boolean(row.event.snapshot_url),
            },
          };
        }
      } catch {
        // Treat database error or latency as "not yet committed"
      }
    }

    // Postgres sink delayed or down: emit alert constructed from envelope with persisted: false
    return {
      alert_id: env.alert_id,
      event_id: env.event_id,
      priority: env.priority,
      status: 'OPEN',
      acknowledged_by: null,
      acknowledged_at: null,
      created_at: env.timestamp,
      persisted: false,
      event: {
        camera_id: env.camera_id,
        event_type: env.event_type,
        threat_score: env.threat_score,
        plate: env.plate,
        timestamp: env.timestamp,
        snapshot_url: env.snapshot_url,
        snapshot_available: env.snapshot_available,
      },
    };
  }
}
