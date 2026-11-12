import type {
  AnalyticsRepo,
  EventTimeSeriesBucket,
  EventTypeCount,
  CameraActivityStats,
  ThreatSummaryStats,
  ResolutionAnalytics,
} from './repo.js';

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
      const s = String(e.severity);
      if (s in severity_counts) {
        severity_counts[s] = (severity_counts[s] ?? 0) + 1;
      }
    }

    const open_alerts_by_priority: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const a of this.alerts) {
      if (a.status === 'OPEN') {
        const p = String(a.priority);
        if (p in open_alerts_by_priority) {
          open_alerts_by_priority[p] = (open_alerts_by_priority[p] ?? 0) + 1;
        }
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

  async getResolutionStats(from?: string, to?: string): Promise<ResolutionAnalytics> {
    let resolvedAlerts = this.alerts.filter(a => a.status === 'RESOLVED' || a.resolution != null);
    if (from) {
      resolvedAlerts = resolvedAlerts.filter(a => (a.resolved_at ?? a.created_at) >= from);
    }
    if (to) {
      resolvedAlerts = resolvedAlerts.filter(a => (a.resolved_at ?? a.created_at) < to);
    }

    const resCounts: Record<string, number> = {};
    const camStats: Record<string, { total: number; fps: number }> = {};
    const ruleStats: Record<string, { total: number; fps: number }> = {};
    const tierStats: Record<string, { total: number; fps: number }> = {};

    let totalResolved = 0;
    let falsePositives = 0;

    for (const a of resolvedAlerts) {
      totalResolved++;
      const res = a.resolution ?? 'RESOLVED';
      resCounts[res] = (resCounts[res] ?? 0) + 1;
      const isFp = res === 'FALSE_POSITIVE';
      if (isFp) falsePositives++;

      const cam = a.event?.camera_id ?? 'UNKNOWN';
      const camObj = camStats[cam] ?? { total: 0, fps: 0 };
      camObj.total++;
      if (isFp) camObj.fps++;
      camStats[cam] = camObj;

      const rule = a.event?.event_type ?? 'UNKNOWN';
      const ruleObj = ruleStats[rule] ?? { total: 0, fps: 0 };
      ruleObj.total++;
      if (isFp) ruleObj.fps++;
      ruleStats[rule] = ruleObj;

      const tier = String(a.priority ?? 'MEDIUM');
      const tierObj = tierStats[tier] ?? { total: 0, fps: 0 };
      tierObj.total++;
      if (isFp) tierObj.fps++;
      tierStats[tier] = tierObj;
    }

    const by_resolution = Object.entries(resCounts).map(([resolution, count]) => ({ resolution, count }));
    const by_camera = Object.entries(camStats).map(([camera_id, v]) => ({
      camera_id,
      total: v.total,
      false_positives: v.fps,
    }));
    const by_rule = Object.entries(ruleStats).map(([rule_type, v]) => ({
      rule_type,
      total: v.total,
      false_positives: v.fps,
    }));
    const by_tier = Object.entries(tierStats).map(([tier, v]) => ({
      tier,
      total: v.total,
      false_positives: v.fps,
    }));

    const fpRate = totalResolved > 0 ? falsePositives / totalResolved : 0.0;

    return {
      total_resolved: totalResolved,
      false_positive_count: falsePositives,
      false_positive_rate: Number(fpRate.toFixed(4)),
      by_resolution,
      by_camera,
      by_rule,
      by_tier,
    };
  }
}
