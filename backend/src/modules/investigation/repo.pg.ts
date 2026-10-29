import type pg from 'pg';
import type { InvestigationRepo, FacetResult, SuggestItem, EventContextResult } from './repo.js';
import type { EventFilters, EventRow } from '../events/repo.js';
import { pgTsToIso } from '../../common/time.js';
import { plateNorm, plateKey, escapeLike } from '../../common/plate.js';

export class PgInvestigationRepo implements InvestigationRepo {
  constructor(private readonly pool: pg.Pool) {}

  private buildWhere(f: EventFilters): { whereClause: string; args: any[] } {
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

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    return { whereClause, args };
  }

  async getFacets(filters: EventFilters): Promise<FacetResult> {
    const base = this.buildWhere(filters);
    const camWhere = this.buildWhere({ ...filters, cameraId: undefined, cameraIds: undefined });
    const typeWhere = this.buildWhere({ ...filters, eventTypes: undefined });
    const sevWhere = this.buildWhere({ ...filters, severities: undefined });

    const [totalRes, camRes, typeRes, sevRes, scoreRes, hoursRes] = await Promise.all([
      this.pool.query(`SELECT count(*) as total FROM events e LEFT JOIN vehicles v ON e.event_id = v.event_id ${base.whereClause} LIMIT 200000`, base.args),
      this.pool.query(`SELECT e.camera_id as value, count(*) as count FROM events e LEFT JOIN vehicles v ON e.event_id = v.event_id ${camWhere.whereClause} GROUP BY 1 ORDER BY 2 DESC LIMIT 50`, camWhere.args),
      this.pool.query(`SELECT e.event_type as value, count(*) as count FROM events e LEFT JOIN vehicles v ON e.event_id = v.event_id ${typeWhere.whereClause} GROUP BY 1 ORDER BY 2 DESC LIMIT 50`, typeWhere.args),
      this.pool.query(`SELECT e.severity as value, count(*) as count FROM events e LEFT JOIN vehicles v ON e.event_id = v.event_id ${sevWhere.whereClause} GROUP BY 1`, sevWhere.args),
      this.pool.query(`SELECT floor(COALESCE(e.threat_score, 0) / 10)::int as bucket, count(*) as count FROM events e LEFT JOIN vehicles v ON e.event_id = v.event_id ${base.whereClause} GROUP BY 1`, base.args),
      this.pool.query(`SELECT EXTRACT(HOUR FROM e.timestamp)::int as hour, count(*) as count FROM events e LEFT JOIN vehicles v ON e.event_id = v.event_id ${base.whereClause} GROUP BY 1`, base.args),
    ]);

    const total = parseInt(totalRes.rows[0]?.total ?? '0', 10);
    const capped = total >= 200000;

    const by_camera = camRes.rows.map(r => ({ value: r.value, count: parseInt(r.count, 10) }));
    const by_event_type = typeRes.rows.map(r => ({ value: r.value, count: parseInt(r.count, 10) }));

    const by_severity = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    sevRes.rows.forEach(r => {
      if (r.value in by_severity) {
        by_severity[r.value as keyof typeof by_severity] = parseInt(r.count, 10);
      }
    });

    const score_histogram = Array.from({ length: 10 }, (_, i) => ({
      from: i * 10,
      to: i === 9 ? 100 : i * 10 + 9,
      count: 0,
    }));
    scoreRes.rows.forEach(r => {
      const idx = Math.min(Math.max(parseInt(r.bucket, 10), 0), 9);
      if (score_histogram[idx]) {
        score_histogram[idx]!.count += parseInt(r.count, 10);
      }
    });

    const hours = Array.from({ length: 24 }, (_, hour) => ({ hour, count: 0 }));
    hoursRes.rows.forEach(r => {
      const h = parseInt(r.hour, 10);
      if (h >= 0 && h < 24 && hours[h]) {
        hours[h]!.count = parseInt(r.count, 10);
      }
    });

    return {
      total,
      by_camera,
      by_event_type,
      by_severity,
      score_histogram,
      hours,
      capped,
    };
  }

  async suggest(kind: 'plate' | 'camera' | 'person', prefix: string, limit = 10): Promise<SuggestItem[]> {
    const esc = escapeLike(prefix.trim().toUpperCase()) + '%';

    if (kind === 'camera') {
      const res = await this.pool.query(
        `SELECT camera_id as val, count(*) as cnt, max(timestamp) as last_seen
         FROM events
         WHERE camera_id ILIKE $1 ESCAPE '\\'
         GROUP BY 1 ORDER BY 3 DESC LIMIT $2`,
        [esc, limit]
      );
      return res.rows.map(r => ({ value: r.val, count: parseInt(r.cnt, 10), last_seen: pgTsToIso(r.last_seen) ?? r.last_seen }));
    }

    if (kind === 'person') {
      const res = await this.pool.query(
        `SELECT COALESCE(metadata->>'person_id', metadata->>'subject_id', metadata->>'reid_candidate_id') as val,
                count(*) as cnt, max(timestamp) as last_seen
         FROM events
         WHERE (metadata->>'person_id' ILIKE $1 ESCAPE '\\' OR metadata->>'subject_id' ILIKE $1 ESCAPE '\\' OR metadata->>'reid_candidate_id' ILIKE $1 ESCAPE '\\')
         GROUP BY 1 ORDER BY 3 DESC LIMIT $2`,
        [esc, limit]
      );
      return res.rows.map(r => ({ value: r.val, count: parseInt(r.cnt, 10), last_seen: pgTsToIso(r.last_seen) ?? r.last_seen }));
    }

    // plate
    const res = await this.pool.query(
      `SELECT COALESCE(plate_norm, plate_norm(plate_number), plate_norm(metadata->>'plate')) as val,
              count(*) as cnt, max(timestamp) as last_seen
       FROM events
       WHERE (COALESCE(plate_norm, plate_norm(plate_number), plate_norm(metadata->>'plate')) LIKE $1 ESCAPE '\\')
       GROUP BY 1 ORDER BY 3 DESC LIMIT $2`,
      [esc, limit]
    );
    return res.rows.map(r => ({ value: r.val, count: parseInt(r.cnt, 10), last_seen: pgTsToIso(r.last_seen) ?? r.last_seen }));
  }

  async getEventContext(eventId: string, windowSeconds = 60): Promise<EventContextResult | null> {
    const eventRes = await this.pool.query(
      `SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
              e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
              COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate,
              v.vehicle_id::text AS vehicle_id,
              a.alert_id, a.status AS alert_status, a.priority AS alert_priority
       FROM events e
       LEFT JOIN vehicles v ON e.event_id = v.event_id
       LEFT JOIN alerts a ON e.event_id = a.event_id
       WHERE e.event_id = $1`,
      [eventId]
    );
    const r = eventRes.rows[0];
    if (!r) return null;

    const event: EventRow = {
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
      metadata: r.metadata ?? {},
    };

    const alert = r.alert_id ? {
      alert_id: r.alert_id,
      status: r.alert_status === 'NEW' ? 'OPEN' : r.alert_status,
      priority: r.alert_priority,
    } : null;

    // Around this camera (±windowSeconds)
    const aroundRes = await this.pool.query(
      `SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
              e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
              COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate
       FROM events e
       LEFT JOIN vehicles v ON e.event_id = v.event_id
       WHERE e.camera_id = $1 AND e.event_id != $2
         AND e.timestamp >= ($3::timestamptz - ($4 || ' seconds')::interval)
         AND e.timestamp <= ($3::timestamptz + ($4 || ' seconds')::interval)
       ORDER BY e.timestamp DESC LIMIT 50`,
      [event.camera_id, eventId, r.timestamp, windowSeconds]
    );

    const same_camera_around: EventRow[] = aroundRes.rows.map(x => ({
      event_id: x.event_id,
      camera_id: x.camera_id,
      event_type: x.event_type,
      track_id: x.track_id ? String(x.track_id) : null,
      severity: x.severity,
      threat_score: Number(x.threat_score ?? 0),
      timestamp: pgTsToIso(x.timestamp) ?? x.timestamp,
      snapshot_path: x.snapshot_path,
      plate: x.plate ?? null,
      metadata: x.metadata ?? {},
    }));

    // Same subject elsewhere (±15 minutes)
    let same_subject_elsewhere: EventRow[] = [];
    if (event.plate || event.vehicle_id) {
      const pKey = event.plate ? plateKey(event.plate) : '';
      const subjectRes = await this.pool.query(
        `SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
                e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
                COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate
         FROM events e
         LEFT JOIN vehicles v ON e.event_id = v.event_id
         WHERE e.camera_id != $1 AND e.event_id != $2
           AND e.timestamp >= ($3::timestamptz - interval '15 minutes')
           AND e.timestamp <= ($3::timestamptz + interval '15 minutes')
           AND (
             ($4 != '' AND (COALESCE(e.plate_key, plate_key(e.plate_number), plate_key(v.plate_number)) = $4))
             OR ($5 != '' AND (v.vehicle_id = $5::bigint OR e.metadata->>'vehicle_id' = $5))
           )
         ORDER BY e.timestamp DESC LIMIT 50`,
        [event.camera_id, eventId, r.timestamp, pKey, event.vehicle_id ?? '']
      );

      same_subject_elsewhere = subjectRes.rows.map(x => ({
        event_id: x.event_id,
        camera_id: x.camera_id,
        event_type: x.event_type,
        track_id: x.track_id ? String(x.track_id) : null,
        severity: x.severity,
        threat_score: Number(x.threat_score ?? 0),
        timestamp: pgTsToIso(x.timestamp) ?? x.timestamp,
        snapshot_path: x.snapshot_path,
        plate: x.plate ?? null,
        metadata: x.metadata ?? {},
      }));
    }

    return {
      event,
      same_camera_around,
      same_subject_elsewhere,
      alert,
    };
  }

  async getJourneyEvents(filter: { plate?: string; vehicleId?: string; from?: string; to?: string }): Promise<EventRow[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (filter.from) {
      where.push(`e.timestamp >= $${idx++}::timestamptz`);
      args.push(filter.from);
    }
    if (filter.to) {
      where.push(`e.timestamp < $${idx++}::timestamptz`);
      args.push(filter.to);
    }

    if (filter.vehicleId) {
      where.push(`(v.vehicle_id = $${idx}::bigint OR e.metadata->>'vehicle_id' = $${idx})`);
      args.push(filter.vehicleId);
      idx++;
    } else if (filter.plate) {
      const key = plateKey(filter.plate);
      where.push(`(COALESCE(e.plate_key, plate_key(e.plate_number), plate_key(v.plate_number)) = $${idx++})`);
      args.push(key);
    }

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    const res = await this.pool.query(
      `SELECT e.event_id, e.camera_id, e.event_type, e.track_id, e.severity,
              e.threat_score, e.timestamp, e.snapshot_path, e.metadata,
              COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number) AS plate,
              v.vehicle_id::text AS vehicle_id
       FROM events e
       LEFT JOIN vehicles v ON e.event_id = v.event_id
       ${whereClause}
       ORDER BY e.timestamp ASC
       LIMIT 5000`,
      args
    );

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
      vehicle_id: r.vehicle_id ?? null,
      metadata: r.metadata ?? {},
    }));
  }
}
