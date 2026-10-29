import type { InvestigationRepo, FacetResult, SuggestItem, EventContextResult } from './repo.js';
import type { EventFilters } from '../events/repo.js';
import { validateTimeRange } from '../../common/time.js';
import { classifyOmniboxQuery } from './query-classifier.js';
import { buildJourney, type Journey } from './journey.js';
import { AppError } from '../../common/errors.js';

export class InvestigationService {
  constructor(private readonly repo: InvestigationRepo) {}

  async getFacets(query: any): Promise<{ data: FacetResult; meta: { capped: boolean } }> {
    validateTimeRange(query.from, query.to);

    let omniboxParsed: Record<string, string> = {};
    if (query.q) {
      omniboxParsed = classifyOmniboxQuery(query.q);
    }

    const cameraId = query.camera_id ?? omniboxParsed.cameraId;
    const cameraIds = cameraId
      ? cameraId.split(',').map((s: string) => s.trim()).filter(Boolean)
      : undefined;

    const eventType = query.event_type ?? omniboxParsed.eventType;
    const eventTypes = eventType
      ? eventType.split(',').map((s: string) => s.trim()).filter(Boolean)
      : undefined;

    const severities = query.severity
      ? query.severity.split(',').map((s: string) => s.trim() as any).filter(Boolean)
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
    };

    const facets = await this.repo.getFacets(filters);
    return {
      data: facets,
      meta: { capped: facets.capped },
    };
  }

  async suggest(kind: 'plate' | 'camera' | 'person', prefix: string, role?: string): Promise<{ data: SuggestItem[] }> {
    if (kind === 'person') {
      if (role !== 'INVESTIGATOR' && role !== 'ADMIN') {
        throw new AppError(403, 'FORBIDDEN', 'Person suggestions are restricted to investigators');
      }
      if (prefix.trim().length < 3) {
        return { data: [] };
      }
    } else {
      if (prefix.trim().length < 2) {
        return { data: [] };
      }
    }

    const items = await this.repo.suggest(kind, prefix, 10);
    return { data: items };
  }

  async getContext(id: string, windowSeconds = 60): Promise<{ data: EventContextResult }> {
    const res = await this.repo.getEventContext(id, windowSeconds);
    if (!res) {
      throw new AppError(404, 'NOT_FOUND', `Event '${id}' not found`);
    }
    return { data: res };
  }

  async getJourney(query: { plate?: string; vehicle_id?: string; from?: string; to?: string }): Promise<{
    data: Journey;
    meta: { truncated: boolean; total_matching: number };
  }> {
    if ((!query.plate && !query.vehicle_id) || (query.plate && query.vehicle_id)) {
      throw new AppError(400, 'VALIDATION_ERROR', 'Exactly one of plate or vehicle_id must be provided');
    }

    const toStr = query.to ?? new Date().toISOString();
    const fromStr = query.from ?? new Date(new Date(toStr).getTime() - 24 * 3600 * 1000).toISOString();
    validateTimeRange(fromStr, toStr);

    const spanMs = new Date(toStr).getTime() - new Date(fromStr).getTime();
    const maxSpanMs = 7 * 24 * 3600 * 1000;
    if (spanMs > maxSpanMs) {
      throw new AppError(400, 'VALIDATION_ERROR', 'Maximum journey time span is 7 days');
    }

    const events = await this.repo.getJourneyEvents({
      plate: query.plate,
      vehicleId: query.vehicle_id,
      from: fromStr,
      to: toStr,
    });

    const isTruncated = events.length >= 5000;
    const cappedEvents = events.slice(0, 5000);

    const journey = buildJourney(cappedEvents.map(e => ({
      event_id: e.event_id,
      camera_id: e.camera_id,
      event_type: e.event_type,
      timestamp: e.timestamp,
      threat_score: e.threat_score,
      plate: e.plate ?? null,
      plate_match: e.plate_match ?? undefined,
    })));

    return {
      data: journey,
      meta: {
        truncated: isTruncated,
        total_matching: events.length,
      },
    };
  }
}
