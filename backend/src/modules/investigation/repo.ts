import type { EventFilters, EventRow } from '../events/repo.js';

export interface FacetItem {
  value: string;
  count: number;
}

export interface FacetResult {
  total: number;
  by_camera: FacetItem[];
  by_event_type: FacetItem[];
  by_severity: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  score_histogram: { from: number; to: number; count: number }[];
  hours: { hour: number; count: number }[];
  capped: boolean;
}

export interface SuggestItem {
  value: string;
  count: number;
  last_seen: string;
}

export interface EventContextResult {
  event: EventRow;
  same_camera_around: EventRow[];
  same_subject_elsewhere: EventRow[];
  alert: { alert_id: string; status: any; priority: any } | null;
}

export interface InvestigationRepo {
  getFacets(filters: EventFilters): Promise<FacetResult>;
  suggest(kind: 'plate' | 'camera' | 'person', prefix: string, limit?: number): Promise<SuggestItem[]>;
  getEventContext(eventId: string, windowSeconds?: number): Promise<EventContextResult | null>;
  getJourneyEvents(filter: { plate?: string; vehicleId?: string; from?: string; to?: string }): Promise<EventRow[]>;
}
