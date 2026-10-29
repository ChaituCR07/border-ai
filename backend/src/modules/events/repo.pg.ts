import type pg from 'pg';
import type { EventsRepo, EventFilters, EventRow } from './repo.js';
import type { Cursor } from '../../common/pagination.js';
import { pgTsToIso } from '../../common/time.js';
import { plateNorm, plateKey, escapeLike } from '../../common/plate.js';

export class PgEventsRepo implements EventsRepo {
  constructor(private readonly pool: pg.Pool) {}

  async list(f: EventFilters, limit: number, cursor?: Cursor): Promise<EventRow[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (f.eventId) {
      where.push(`e.event_id = $${idx++}`);
      args.push(f.eventId);
    }
    if (f.cameraId) {
      where.push(`e.camera_id = $${idx++}`);
      args.push(f.cameraId);
    }
    if (f.cameraIds && f.cameraIds.length > 0) {
      where.push(`e.camera_id = ANY($${idx++})`);
      args.push(f.cameraIds);
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
    if (f.vehicleId) {
      where.push(`(v.vehicle_id = $${idx}::bigint OR e.metadata->>'vehicle_id' = $${idx})`);
      args.push(f.vehicleId);
      idx++;
    }
    if (f.personId) {
      where.push(`(e.metadata->>'person_id' = $${idx} OR e.metadata->>'reid_candidate_id' = $${idx} OR e.metadata->>'subject_id' = $${idx})`);
      args.push(f.personId);
      idx++;
    }

    let selectPlateMatch = 'NULL::text AS plate_match';
    if (f.plate) {
      const mode = f.plateMatch ?? 'lookalike';
      const norm = plateNorm(f.plate);
      const key = plateKey(f.plate);
      const pre = escapeLike(norm) + '%';
      const con = '%' + escapeLike(norm) + '%';

      const pNorm = `$${idx++}`;
      args.push(norm);
      const pKey = `$${idx++}`;
      args.push(key);
      const pPre = `$${idx++}`;
      args.push(pre);
      const pCon = `$${idx++}`;
      args.push(con);

      selectPlateMatch = `CASE
        WHEN (COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) = ${pNorm}) THEN 'exact'
        WHEN (COALESCE(e.plate_key, plate_key(e.plate_number), plate_key(v.plate_number)) = ${pKey}) THEN 'lookalike'
        WHEN (COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) LIKE ${pPre} ESCAPE '\\') THEN 'prefix'
        WHEN (COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) LIKE ${pCon} ESCAPE '\\') THEN 'partial'
        ELSE NULL
      END AS plate_match`;

      if (mode === 'exact') {
        where.push(`(COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) = ${pNorm})`);
      } else if (mode === 'lookalike') {
        where.push(`(COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) = ${pNorm} OR COALESCE(e.plate_key, plate_key(e.plate_number), plate_key(v.plate_number)) = ${pKey})`);
      } else if (mode === 'prefix') {
        where.push(`(COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) LIKE ${pPre} ESCAPE '\\')`);
      } else if (mode === 'contains') {
        where.push(`(COALESCE(e.plate_norm, plate_norm(e.plate_number), plate_norm(v.plate_number)) LIKE ${pCon} ESCAPE '\\')`);
      }
    }

    if (f.timeFrom && f.timeTo) {
      const tz = f.tz || 'UTC';
      const t = `((e."timestamp" AT TIME ZONE $${idx++})::time)`;
      args.push(tz);
      const fromParam = `$${idx++}::time`;
      args.push(f.timeFrom);
      const toParam = `$${idx++}::time`;
      args.push(f.timeTo);

      if (f.timeFrom <= f.timeTo) {
        where.push(`${t} >= ${fromParam} AND ${t} < ${toParam}`);
      } else {
        where.push(`(${t} >= ${fromParam} OR ${t} < ${toParam})`);
      }
    }

    let orderByClause = 'ORDER BY e.timestamp DESC, e.event_id DESC';
    if (f.sort === 'score') {
      if (cursor && cursor.score !== undefined) {
        where.push(`(e.threat_score, e.timestamp, e.event_id) < ($${idx++}::int, $${idx++}::timestamptz, $${idx++}::text)`);
        args.push(cursor.score, cursor.t, cursor.id);
      }
      orderByClause = 'ORDER BY e.threat_score DESC, e.timestamp DESC, e.event_id DESC';
    } else {
      if (cursor) {
        where.push(`(e.timestamp, e.event_id) < ($${idx++}::timestamptz, $${idx++}::text)`);
        args.push(cursor.t, cursor.id);
      }
      orderByClause = 'ORDER BY e.timestamp DESC, e.event_id DESC';
    }

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    const sql = `
      SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
             e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
             COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate,
             v.vehicle_id::text AS vehicle_id,
             COALESCE(e.metadata->>'person_id', e.metadata->>'reid_candidate_id', e.metadata->>'subject_id') AS person_id,
             ${selectPlateMatch}
      FROM events e
      LEFT JOIN vehicles v ON e.event_id = v.event_id
      ${whereClause}
      ${orderByClause}
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
      plate_match: r.plate_match ?? null,
      vehicle_id: r.vehicle_id ?? null,
      person_id: r.person_id ?? null,
      metadata: r.metadata ?? {},
    }));
  }

  async getById(id: string): Promise<{ row: EventRow; alert?: { alert_id: string; status: any; priority: any } | null } | null> {
    const sql = `
      SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
             e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
             COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate,
             v.vehicle_id::text AS vehicle_id,
             COALESCE(e.metadata->>'person_id', e.metadata->>'reid_candidate_id', e.metadata->>'subject_id') AS person_id,
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
      vehicle_id: r.vehicle_id ?? null,
      person_id: r.person_id ?? null,
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
