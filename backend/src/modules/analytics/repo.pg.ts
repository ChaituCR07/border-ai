import type pg from 'pg';
import type { AnalyticsRepo, EventTimeSeriesBucket, EventTypeCount, CameraActivityStats, ThreatSummaryStats } from './repo.js';
import { pgTsToIso } from '../../common/time.js';

export class PgAnalyticsRepo implements AnalyticsRepo {
  constructor(private readonly pool: pg.Pool) {}

  async getEventTimeseries(
    from: string,
    to: string,
    bucket: 'hour' | 'day',
    cameraId?: string
  ): Promise<{ buckets: EventTimeSeriesBucket[]; by_type: EventTypeCount[] }> {
    const interval = bucket === 'day' ? '1 day' : '1 hour';
    const where: string[] = ['e.timestamp >= $1::timestamptz', 'e.timestamp < $2::timestamptz'];
    const args: any[] = [from, to];

    if (cameraId) {
      where.push(`e.camera_id = $3`);
      args.push(cameraId);
    }

    const seriesSql = `
      SELECT date_bin($1::interval, e.timestamp, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS bucket,
             count(*)::int AS total,
             count(*) FILTER (WHERE e.severity = 'CRITICAL')::int AS critical,
             count(*) FILTER (WHERE e.severity = 'HIGH')::int AS high,
             count(*) FILTER (WHERE e.severity = 'MEDIUM')::int AS medium,
             count(*) FILTER (WHERE e.severity = 'LOW')::int AS low
      FROM events e
      WHERE ${where.join(' AND ')}
      GROUP BY 1
      ORDER BY 1 ASC
    `;

    const res = await this.pool.query(seriesSql, [interval, ...args]);
    const buckets: EventTimeSeriesBucket[] = res.rows.map(r => ({
      bucket: pgTsToIso(r.bucket) ?? r.bucket,
      total: Number(r.total),
      critical: Number(r.critical),
      high: Number(r.high),
      medium: Number(r.medium),
      low: Number(r.low),
    }));

    const typeSql = `
      SELECT e.event_type, count(*)::int AS count
      FROM events e
      WHERE ${where.join(' AND ')}
      GROUP BY e.event_type
      ORDER BY count DESC
      LIMIT 10
    `;
    const typeRes = await this.pool.query(typeSql, args);
    const by_type: EventTypeCount[] = typeRes.rows.map(r => ({
      event_type: r.event_type,
      count: Number(r.count),
    }));

    return { buckets, by_type };
  }

  async getCameraStats(from?: string, to?: string): Promise<CameraActivityStats[]> {
    const timeFilter = from && to ? `AND e.timestamp >= $1::timestamptz AND e.timestamp < $2::timestamptz` : '';
    const args = from && to ? [from, to] : [];

    const sql = `
      SELECT c.camera_id,
             count(e.event_id)::int AS events,
             count(a.alert_id) FILTER (WHERE a.status = 'OPEN')::int AS alerts_open,
             COALESCE(max(e.threat_score), 0)::int AS max_threat_score,
             max(e.timestamp) AS last_event_at
      FROM cameras c
      LEFT JOIN events e ON c.camera_id = e.camera_id ${timeFilter}
      LEFT JOIN alerts a ON e.event_id = a.event_id
      GROUP BY c.camera_id
      ORDER BY c.camera_id ASC
    `;

    const res = await this.pool.query(sql, args);
    return res.rows.map(r => ({
      camera_id: r.camera_id,
      events: Number(r.events),
      alerts_open: Number(r.alerts_open),
      max_threat_score: Number(r.max_threat_score),
      last_event_at: pgTsToIso(r.last_event_at),
    }));
  }

  async getThreatStats(from: string, to: string, cameraId?: string): Promise<ThreatSummaryStats> {
    const where: string[] = ['e.timestamp >= $1::timestamptz', 'e.timestamp < $2::timestamptz'];
    const args: any[] = [from, to];

    if (cameraId) {
      where.push(`e.camera_id = $3`);
      args.push(cameraId);
    }

    const sevSql = `
      SELECT e.severity, count(*)::int AS count
      FROM events e
      WHERE ${where.join(' AND ')}
      GROUP BY e.severity
    `;
    const sevRes = await this.pool.query(sevSql, args);
    const severity_counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const r of sevRes.rows) {
      severity_counts[r.severity] = Number(r.count);
    }

    const alertSql = `
      SELECT a.priority, count(*)::int AS count
      FROM alerts a
      JOIN events e ON a.event_id = e.event_id
      WHERE a.status = 'OPEN' AND ${where.join(' AND ')}
      GROUP BY a.priority
    `;
    const alertRes = await this.pool.query(alertSql, args);
    const open_alerts_by_priority: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const r of alertRes.rows) {
      open_alerts_by_priority[r.priority] = Number(r.count);
    }

    const histSql = `
      SELECT width_bucket(e.threat_score, 0, 100, 10) AS bucket,
             count(*)::int AS count
      FROM events e
      WHERE ${where.join(' AND ')}
      GROUP BY bucket
      ORDER BY bucket ASC
    `;
    const histRes = await this.pool.query(histSql, args);
    const histMap = new Map<number, number>();
    for (const r of histRes.rows) {
      histMap.set(Number(r.bucket), Number(r.count));
    }
    const score_histogram: { from: number; to: number; count: number }[] = [];
    for (let i = 1; i <= 10; i++) {
      score_histogram.push({
        from: (i - 1) * 10,
        to: i === 10 ? 100 : i * 10 - 1,
        count: histMap.get(i) ?? 0,
      });
    }

    const topEventsSql = `
      SELECT e.event_type, count(*)::int AS count
      FROM events e
      WHERE ${where.join(' AND ')}
      GROUP BY e.event_type
      ORDER BY count DESC
      LIMIT 5
    `;
    const topEventsRes = await this.pool.query(topEventsSql, args);
    const top_event_types = topEventsRes.rows.map(r => ({
      event_type: r.event_type,
      count: Number(r.count),
    }));

    const topPlatesSql = `
      SELECT COALESCE(e.metadata->>'plate', v.plate_number) AS plate,
             count(*)::int AS events,
             max(e.threat_score)::int AS max_score
      FROM events e
      LEFT JOIN vehicles v ON e.event_id = v.event_id
      WHERE (e.metadata->>'plate' IS NOT NULL OR v.plate_number IS NOT NULL)
        AND ${where.join(' AND ')}
      GROUP BY 1
      ORDER BY events DESC, max_score DESC
      LIMIT 5
    `;
    const topPlatesRes = await this.pool.query(topPlatesSql, args);
    const top_plates = topPlatesRes.rows
      .filter(r => Boolean(r.plate))
      .map(r => ({
        plate: r.plate,
        events: Number(r.events),
        max_score: Number(r.max_score),
      }));

    return {
      severity_counts,
      open_alerts_by_priority,
      score_histogram,
      top_event_types,
      top_plates,
    };
  }
}
