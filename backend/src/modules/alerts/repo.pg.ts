import type pg from 'pg';
import type { AlertsRepo, AlertFilters } from './repo.js';
import type { AlertResource } from '../../types/domain.js';
import type { Cursor } from '../../common/pagination.js';
import { pgTsToIso } from '../../common/time.js';

export class PgAlertsRepo implements AlertsRepo {
  constructor(private readonly pool: pg.Pool) {}

  private mapRow(r: any): AlertResource {
    return {
      alert_id: r.alert_id,
      event_id: r.event_id,
      priority: r.priority,
      status: r.status === 'NEW' ? 'OPEN' : r.status,
      acknowledged_by: r.acknowledged_by ?? null,
      acknowledged_at: pgTsToIso(r.acknowledged_at),
      created_at: pgTsToIso(r.created_at) ?? r.created_at,
      event: {
        camera_id: r.camera_id,
        event_type: r.event_type,
        threat_score: Number(r.threat_score ?? 0),
        plate: r.plate ?? null,
        snapshot_url: r.snapshot_path ? `/api/snapshots/${r.snapshot_path.replace(/^\/+/, '')}` : null,
      },
    };
  }

  async list(f: AlertFilters, limit: number, cursor?: Cursor): Promise<AlertResource[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (f.status) {
      if (f.status === 'OPEN') {
        where.push(`a.status IN ('NEW', 'OPEN')`);
      } else {
        where.push(`a.status = $${idx++}`);
        args.push(f.status);
      }
    }
    if (f.priority) {
      where.push(`a.priority = $${idx++}`);
      args.push(f.priority);
    }
    if (f.cameraId) {
      where.push(`a.camera_id = $${idx++}`);
      args.push(f.cameraId);
    }
    if (f.from) {
      where.push(`a.created_at >= $${idx++}::timestamptz`);
      args.push(f.from);
    }
    if (f.to) {
      where.push(`a.created_at < $${idx++}::timestamptz`);
      args.push(f.to);
    }
    if (cursor) {
      where.push(`(a.created_at, a.alert_id) < ($${idx++}::timestamptz, $${idx++}::text)`);
      args.push(cursor.t, cursor.id);
    }

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    const sql = `
      SELECT a.alert_id, a.event_id, a.camera_id, a.priority, a.status, a.acknowledged_by, a.acknowledged_at, a.created_at,
             e.event_type, e.threat_score, e.snapshot_path,
             COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate
      FROM alerts a
      JOIN events e ON a.event_id = e.event_id
      LEFT JOIN vehicles v ON e.event_id = v.event_id
      ${whereClause}
      ORDER BY a.created_at DESC, a.alert_id DESC
      LIMIT $${idx}
    `;
    args.push(limit);

    const res = await this.pool.query(sql, args);
    return res.rows.map(r => this.mapRow(r));
  }

  async getById(alertId: string): Promise<AlertResource | null> {
    const sql = `
      SELECT a.alert_id, a.event_id, a.camera_id, a.priority, a.status, a.acknowledged_by, a.acknowledged_at, a.created_at,
             e.event_type, e.threat_score, e.snapshot_path,
             COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate
      FROM alerts a
      JOIN events e ON a.event_id = e.event_id
      LEFT JOIN vehicles v ON e.event_id = v.event_id
      WHERE a.alert_id = $1::text
    `;
    const res = await this.pool.query(sql, [alertId]);
    return res.rows[0] ? this.mapRow(res.rows[0]) : null;
  }

  async acknowledge(alertId: string, acknowledgedBy: string): Promise<{ alert: AlertResource; updated: boolean } | null> {
    // Atomic race-safe UPDATE matching NEW or OPEN
    const updateSql = `
      UPDATE alerts
      SET status = 'ACKNOWLEDGED', acknowledged_by = $2, acknowledged_at = now(), updated_at = now()
      WHERE alert_id = $1::text AND status IN ('NEW', 'OPEN')
      RETURNING alert_id
    `;
    const updateRes = await this.pool.query(updateSql, [alertId, acknowledgedBy]);

    if (updateRes.rowCount && updateRes.rowCount > 0) {
      const full = await this.getById(alertId);
      return full ? { alert: full, updated: true } : null;
    }

    // If 0 rows updated, check if it exists (idempotent 200 or 404)
    const existing = await this.getById(alertId);
    if (!existing) return null;
    return { alert: existing, updated: false };
  }
}
