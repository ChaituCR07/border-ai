import type { AnalyticsRepo } from './repo.js';
import { validateTimeRange } from '../../common/time.js';

export class AnalyticsService {
  constructor(private readonly repo: AnalyticsRepo) {}

  private resolveRange(from?: string, to?: string): { from: string; to: string } {
    validateTimeRange(from, to);
    const now = new Date();
    const resolvedTo = to ? new Date(to) : now;
    const resolvedFrom = from ? new Date(from) : new Date(resolvedTo.getTime() - 24 * 60 * 60 * 1000);
    return {
      from: resolvedFrom.toISOString(),
      to: resolvedTo.toISOString(),
    };
  }

  private zeroFill(
    buckets: { bucket: string; total: number; critical: number; high: number; medium: number; low: number }[],
    from: string,
    to: string,
    step: 'hour' | 'day'
  ) {
    const map = new Map(buckets.map(b => [b.bucket.substring(0, step === 'day' ? 10 : 13), b]));
    const result: typeof buckets = [];

    const cur = new Date(from);
    const end = new Date(to);

    // Align cur to bucket
    if (step === 'day') {
      cur.setUTCHours(0, 0, 0, 0);
    } else {
      cur.setUTCMinutes(0, 0, 0);
    }

    while (cur < end) {
      const key = cur.toISOString().substring(0, step === 'day' ? 10 : 13);
      const isoBucket = step === 'day'
        ? `${cur.toISOString().substring(0, 10)}T00:00:00.000000Z`
        : `${cur.toISOString().substring(0, 13)}:00:00.000000Z`;

      const existing = map.get(key);
      if (existing) {
        result.push(existing);
      } else {
        result.push({
          bucket: isoBucket,
          total: 0,
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
        });
      }

      if (step === 'day') {
        cur.setUTCDate(cur.getUTCDate() + 1);
      } else {
        cur.setUTCHours(cur.getUTCHours() + 1);
      }
    }

    return result;
  }

  async getEvents(query: any) {
    const { from, to } = this.resolveRange(query.from, query.to);
    const bucket = query.bucket ?? 'hour';
    const raw = await this.repo.getEventTimeseries(from, to, bucket, query.camera_id);

    const filled = this.zeroFill(raw.buckets, from, to, bucket);

    return {
      bucket_tz: 'UTC' as const,
      buckets: filled,
      by_type: raw.by_type,
    };
  }

  async getCameras(query: any) {
    const from = query.from;
    const to = query.to;
    if (from || to) {
      validateTimeRange(from, to);
    }
    const data = await this.repo.getCameraStats(from, to);
    return { data };
  }

  async getThreats(query: any) {
    const { from, to } = this.resolveRange(query.from, query.to);
    const data = await this.repo.getThreatStats(from, to, query.camera_id);
    return { data };
  }
}
