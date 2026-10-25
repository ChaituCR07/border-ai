import type pg from 'pg';
import type { EventsRepo, EventFilters, EventRow } from './repo.js';
import type { Cursor } from '../../common/pagination.js';
import { pgTsToIso } from '../../common/time.js';

export class PgEventsRepo implements EventsRepo {
  constructor(private readonly pool: pg.Pool) {}

  async list(f: EventFilters, limit: number, cursor?: Cursor): Promise<EventRow[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (f.cameraId) {
      where.push(`e.camera_id = $${idx++}`);
      args.push(f.cameraId);
    }
    if (f.eventTypes && f.eventTypes.length > 0) {
      where.push(`e.event_type = ANY($${idx++})`);
      args.push(f.eventTypes);
    }
    if (f.severities && f.severities.length > 0) {
      where.push(`e.severity = ANY($${idx++})`);
      args.push(f.severities);
    }
    if (f.minScore !== undefined) {
      where.push(`e.threat_score >= $${idx++}`);
      args.push(f.minScore);
    }
    if (f.maxScore !== undefined) {
      where.push(`e.threat_score <= $${idx++}`);
      args.push(f.maxScore);
    }
    if (f.from) {
      where.push(`e.timestamp >= $${idx++}::timestamptz`);
      args.push(f.from);
    }
    if (f.to) {
      where.push(`e.timestamp < $${idx++}::timestamptz`);
      args.push(f.to);
    }
    if (f.trackId) {
      where.push(`e.track_id = $${idx++}`);
      args.push(f.trackId);
    }
    if (f.plate) {
      where.push(`(e.plate_number = $${idx} OR e.metadata->>'plate' = $${idx} OR v.plate_number = $${idx})`);
      args.push(f.plate);
      idx++;
    }
    if (cursor) {
      where.push(`(e.timestamp, e.event_id) < ($${idx++}::timestamptz, $${idx++}::text)`);
      args.push(cursor.t, cursor.id);
    }

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    const sql = `
      SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
             e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
             COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate
      FROM events e
      LEFT JOIN vehicles v ON e.event_id = v.event_id
      ${whereClause}
      ORDER BY e.timestamp DESC, e.event_id DESC
      LIMIT $${idx}
    `;
    args.push(limit);

    const res = await this.pool.query(sql, args);
    return res.rows.map(r => ({
      event_id: r.event_id,
      camera_id: r.camera_id,
      event_type: r.event_type,
      track_id: r.track_id ? String(r.track_id) : null,
      severity: r.severity,
      threat_score: Number(r.threat_score ?? 0),
      timestamp: pgTsToIso(r.timestamp) ?? r.timestamp,
      snapshot_path: r.snapshot_path,
      plate: r.plate ?? null,
      metadata: r.metadata ?? {},
    }));
  }

  async getById(id: string): Promise<{ row: EventRow; alert?: { alert_id: string; status: any; priority: any } | null } | null> {
    const sql = `
      SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
             e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
             COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate,
             a.alert_id, a.status AS alert_status, a.priority AS alert_priority
      FROM events e
      LEFT JOIN vehicles v ON e.event_id = v.event_id
      LEFT JOIN alerts a ON e.event_id = a.event_id
      WHERE e.event_id = $1::text
    `;
    const res = await this.pool.query(sql, [id]);
    const r = res.rows[0];
    if (!r) return null;

    const row: EventRow = {
      event_id: r.event_id,
      camera_id: r.camera_id,
      event_type: r.event_type,
      track_id: r.track_id ? String(r.track_id) : null,
      severity: r.severity,
      threat_score: Number(r.threat_score ?? 0),
      timestamp: pgTsToIso(r.timestamp) ?? r.timestamp,
      snapshot_path: r.snapshot_path,
      plate: r.plate ?? null,
      metadata: r.metadata ?? {},
    };

    const alert = r.alert_id ? {
      alert_id: r.alert_id,
      status: r.alert_status === 'NEW' ? 'OPEN' : r.alert_status,
      priority: r.alert_priority,
    } : null;

    return { row, alert };
  }
}
