import fs from 'node:fs';
import path from 'node:path';
import type { EventsRepo, EventFilters, EventRow } from './repo.js';
import type { EventResource, EventDetailResource, Severity } from '../../types/domain.js';
import { clampLimit, decodeCursor, encodeCursor, type Cursor, type PaginatedResponse } from '../../common/pagination.js';
import { notFound, AppError } from '../../common/errors.js';
import { validateTimeRange } from '../../common/time.js';
import { normalisePlate } from '../../common/plate.js';

export class EventsService {
  constructor(
    private readonly repo: EventsRepo,
    private readonly snapshotDir: string
  ) {}

  private checkSnapshotAvailability(snapshotPath: string | null): boolean {
    if (!snapshotPath) return false;
    try {
      const root = path.resolve(this.snapshotDir);
      const abs = path.resolve(root, snapshotPath);
      if (!abs.startsWith(root + path.sep)) return false;
      return fs.existsSync(abs);
    } catch {
      return false;
    }
  }

  private mapResource(r: EventRow): EventResource {
    const hasSnapshot = Boolean(r.snapshot_path);
    const snapshotAvailable = this.checkSnapshotAvailability(r.snapshot_path);
    return {
      event_id: r.event_id,
      camera_id: r.camera_id,
      event_type: r.event_type,
      track_id: r.track_id,
      severity: r.severity,
      threat_score: r.threat_score,
      timestamp: r.timestamp,
      snapshot_url: r.snapshot_path ? `/api/snapshots/${r.snapshot_path.replace(/^\/+/, '')}` : null,
      has_snapshot: hasSnapshot,
      snapshot_available: snapshotAvailable,
      plate: r.plate ?? null,
    };
  }

  async list(query: any): Promise<PaginatedResponse<EventResource>> {
    validateTimeRange(query.from, query.to);

    const limit = clampLimit(query.limit, 50, 200);
    const cursor: Cursor | undefined = query.cursor ? decodeCursor(query.cursor) : undefined;

    const filters: EventFilters = {
      cameraId: query.camera_id,
      eventTypes: query.event_type ? query.event_type.split(',').map((s: string) => s.trim()) : undefined,
      severities: query.severity ? query.severity.split(',').map((s: string) => s.trim() as Severity) : undefined,
      minScore: query.min_score,
      maxScore: query.max_score,
      from: query.from,
      to: query.to,
      trackId: query.track_id,
      plate: query.plate ? normalisePlate(query.plate) : undefined,
    };

    // Keyset pagination: fetch limit + 1
    const rows = await this.repo.list(filters, limit + 1, cursor);
    const hasMore = rows.length > limit;
    const pageRows = hasMore ? rows.slice(0, limit) : rows;

    const nextCursor = hasMore && pageRows.length > 0
      ? encodeCursor({
          t: pageRows[pageRows.length - 1]!.timestamp,
          id: pageRows[pageRows.length - 1]!.event_id,
        })
      : null;

    return {
      data: pageRows.map(r => this.mapResource(r)),
      meta: {
        limit,
        next_cursor: nextCursor,
        has_more: hasMore,
      },
    };
  }

  async get(id: string): Promise<EventDetailResource> {
    const res = await this.repo.getById(id);
    if (!res) throw notFound(`Event '${id}'`);

    const base = this.mapResource(res.row);
    const metadata = res.row.metadata || {};
    const explanation = (metadata.explanation ?? metadata.score_breakdown ?? null) as Record<string, unknown> | null;

    return {
      ...base,
      explanation,
      metadata,
      alert: res.alert ?? null,
    };
  }
}
