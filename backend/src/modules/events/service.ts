import fs from 'node:fs';
import path from 'node:path';
import type { EventsRepo, EventFilters, EventRow } from './repo.js';
import type { EventResource, EventDetailResource, Severity } from '../../types/domain.js';
import { clampLimit, decodeCursor, encodeCursor, type Cursor, type PaginatedResponse } from '../../common/pagination.js';
import { notFound, AppError } from '../../common/errors.js';
import { validateTimeRange } from '../../common/time.js';
import { classifyOmniboxQuery } from '../investigation/query-classifier.js';

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
      plate_match: r.plate_match ?? null,
      vehicle_id: r.vehicle_id ?? null,
      person_id: r.person_id ?? null,
    };
  }

  async list(query: any): Promise<PaginatedResponse<EventResource>> {
    validateTimeRange(query.from, query.to);

    // Time-of-day requires explicit from/to dates (ADR 0023 / Pitfall S2)
    if (query.time_from || query.time_to) {
      if (!query.from || !query.to) {
        throw new AppError(
          400,
          'VALIDATION_ERROR',
          'Date range (from and to) is required when using time-of-day filters'
        );
      }
      if (!query.time_from || !query.time_to) {
        throw new AppError(
          400,
          'VALIDATION_ERROR',
          'Both time_from and time_to are required for time-of-day filtering'
        );
      }
    }

    if (query.tz) {
      const validZones = typeof Intl.supportedValuesOf === 'function'
        ? Intl.supportedValuesOf('timeZone')
        : ['UTC'];
      if (query.tz !== 'UTC' && !validZones.includes(query.tz)) {
        throw new AppError(400, 'VALIDATION_ERROR', `Invalid timezone '${query.tz}'`);
      }
    }

    // Person ID lookup requires justification (ADR 0024)
    if (query.person_id) {
      if (!query.purpose || query.purpose.trim().length < 5) {
        throw new AppError(
          422,
          'PURPOSE_REQUIRED',
          'A purpose (case reference) is required for person searches'
        );
      }
    }

    // Omnibox free text query fallback
    let omniboxParsed: Record<string, string> = {};
    if (query.q) {
      omniboxParsed = classifyOmniboxQuery(query.q);
    }

    const sortMode: 'time' | 'score' = query.sort === 'score' ? 'score' : 'time';
    const limit = clampLimit(query.limit, 50, 200);
    const cursor: Cursor | undefined = query.cursor ? decodeCursor(query.cursor, sortMode) : undefined;

    const cameraId = query.camera_id ?? omniboxParsed.cameraId;
    const cameraIds = cameraId
      ? cameraId.split(',').map((s: string) => s.trim()).filter(Boolean)
      : undefined;

    const eventType = query.event_type ?? omniboxParsed.eventType;
    const eventTypes = eventType
      ? eventType.split(',').map((s: string) => s.trim()).filter(Boolean)
      : undefined;

    const severities = query.severity
      ? query.severity.split(',').map((s: string) => s.trim() as Severity).filter(Boolean)
      : undefined;

    const plate = query.plate ?? omniboxParsed.plate;
    const plateMatch = query.plate_match ?? (omniboxParsed.plateMatch as any) ?? 'lookalike';

    const filters: EventFilters = {
      eventId: omniboxParsed.eventId,
      cameraId: cameraIds && cameraIds.length === 1 ? cameraIds[0] : undefined,
      cameraIds: cameraIds && cameraIds.length > 1 ? cameraIds : undefined,
      eventTypes,
      severities,
      minScore: query.min_score,
      maxScore: query.max_score,
      from: query.from,
      to: query.to,
      trackId: query.track_id,
      plate,
      plateMatch,
      vehicleId: query.vehicle_id,
      personId: query.person_id,
      timeFrom: query.time_from,
      timeTo: query.time_to,
      tz: query.tz,
      sort: sortMode,
    };

    // Keyset pagination: fetch limit + 1
    const rows = await this.repo.list(filters, limit + 1, cursor);
    const hasMore = rows.length > limit;
    const pageRows = hasMore ? rows.slice(0, limit) : rows;

    let nextCursor: string | null = null;
    if (hasMore && pageRows.length > 0) {
      const last = pageRows[pageRows.length - 1]!;
      nextCursor = encodeCursor(
        sortMode === 'score'
          ? {
              sort: 'score',
              score: last.threat_score,
              t: last.timestamp,
              id: last.event_id,
            }
          : {
              sort: 'time',
              t: last.timestamp,
              id: last.event_id,
            }
      );
    }

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

  async getContext(
    id: string,
    windowSeconds = 60,
    role?: string
  ): Promise<{
    data: {
      event: EventResource;
      same_camera_around: EventResource[];
      same_subject_elsewhere: EventResource[];
      alert?: { alert_id: string; status: any; priority: any } | null;
    };
  }> {
    const isInvestigator = role === 'INVESTIGATOR' || role === 'ADMIN';
    const ctx = await this.repo.getContext(id, windowSeconds, isInvestigator);
    if (!ctx) throw notFound(`Event '${id}'`);

    return {
      data: {
        event: this.mapResource(ctx.event),
        same_camera_around: ctx.sameCameraAround.map(r => this.mapResource(r)),
        same_subject_elsewhere: ctx.sameSubjectElsewhere.map(r => this.mapResource(r)),
        alert: ctx.alert ?? null,
      },
    };
  }
}
