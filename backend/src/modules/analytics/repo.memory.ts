import type { AnalyticsRepo, EventTimeSeriesBucket, EventTypeCount, CameraActivityStats, ThreatSummaryStats } from './repo.js';

export class InMemoryAnalyticsRepo implements AnalyticsRepo {
  private events: any[] = [];
  private alerts: any[] = [];
  private cameras: any[] = [];

  seed(events: any[], alerts: any[], cameras: any[]) {
    this.events = events;
    this.alerts = alerts;
    this.cameras = cameras;
  }

  async getEventTimeseries(
    from: string,
    to: string,
    bucket: 'hour' | 'day',
    cameraId?: string
  ): Promise<{ buckets: EventTimeSeriesBucket[]; by_type: EventTypeCount[] }> {
    let evts = this.events.filter(e => e.timestamp >= from && e.timestamp < to);
    if (cameraId) evts = evts.filter(e => e.camera_id === cameraId);

    const bucketMap = new Map<string, EventTimeSeriesBucket>();
    const typeMap = new Map<string, number>();

    for (const e of evts) {
      const d = new Date(e.timestamp);
      let key = '';
      if (bucket === 'day') {
        key = `${d.toISOString().substring(0, 10)}T00:00:00.000000Z`;
      } else {
        key = `${d.toISOString().substring(0, 13)}:00:00.000000Z`;
      }

      if (!bucketMap.has(key)) {
        bucketMap.set(key, { bucket: key, total: 0, critical: 0, high: 0, medium: 0, low: 0 });
      }
      const b = bucketMap.get(key)!;
      b.total++;
      if (e.severity === 'CRITICAL') b.critical++;
      else if (e.severity === 'HIGH') b.high++;
      else if (e.severity === 'MEDIUM') b.medium++;
      else if (e.severity === 'LOW') b.low++;

      typeMap.set(e.event_type, (typeMap.get(e.event_type) ?? 0) + 1);
    }

    const buckets = Array.from(bucketMap.values()).sort((a, b) => a.bucket.localeCompare(b.bucket));
    const by_type = Array.from(typeMap.entries())
      .map(([event_type, count]) => ({ event_type, count }))
      .sort((a, b) => b.count - a.count);

    return { buckets, by_type };
  }

  async getCameraStats(): Promise<CameraActivityStats[]> {
    return this.cameras.map(c => {
      const camEvts = this.events.filter(e => e.camera_id === c.camera_id);
      const camAlerts = this.alerts.filter(a => a.event?.camera_id === c.camera_id && a.status === 'OPEN');
      const maxScore = camEvts.reduce((acc, e) => Math.max(acc, e.threat_score ?? 0), 0);
      const lastEvent = camEvts.length > 0 ? camEvts[camEvts.length - 1].timestamp : null;

      return {
        camera_id: c.camera_id,
        events: camEvts.length,
        alerts_open: camAlerts.length,
        max_threat_score: maxScore,
        last_event_at: lastEvent,
      };
    });
  }

  async getThreatStats(from: string, to: string, cameraId?: string): Promise<ThreatSummaryStats> {
    let evts = this.events.filter(e => e.timestamp >= from && e.timestamp < to);
    if (cameraId) evts = evts.filter(e => e.camera_id === cameraId);

    const severity_counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const e of evts) {
      if (e.severity in severity_counts) severity_counts[e.severity]++;
    }

    const open_alerts_by_priority: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const a of this.alerts) {
      if (a.status === 'OPEN' && a.priority in open_alerts_by_priority) {
        open_alerts_by_priority[a.priority]++;
      }
    }

    const histogram = Array.from({ length: 10 }, (_, i) => ({
      from: i * 10,
      to: i === 9 ? 100 : (i + 1) * 10 - 1,
      count: 0,
    }));
    for (const e of evts) {
      const score = Math.min(Math.max(e.threat_score ?? 0, 0), 100);
      const idx = Math.min(Math.floor(score / 10), 9);
      histogram[idx]!.count++;
    }

    return {
      severity_counts,
      open_alerts_by_priority,
      score_histogram: histogram,
      top_event_types: [],
      top_plates: [],
    };
  }
}
