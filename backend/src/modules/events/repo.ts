import type { Severity, EventResource, EventDetailResource } from '../../types/domain.js';
import type { Cursor } from '../../common/pagination.js';

export interface EventFilters {
  cameraId?: string;
  eventTypes?: string[];
  severities?: Severity[];
  minScore?: number;
  maxScore?: number;
  from?: string;
  to?: string;
  trackId?: string;
  plate?: string;
}

export interface EventRow {
  event_id: string;
  camera_id: string;
  event_type: string;
  track_id: string | null;
  severity: Severity;
  threat_score: number;
  timestamp: string;
  snapshot_path: string | null;
  plate?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EventsRepo {
  list(filters: EventFilters, limit: number, cursor?: Cursor): Promise<EventRow[]>;
  getById(id: string): Promise<{ row: EventRow; alert?: { alert_id: string; status: any; priority: any } | null } | null>;
}
