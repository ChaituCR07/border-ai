import type { EventsRepo, EventFilters, EventRow } from './repo.js';
import type { Cursor } from '../../common/pagination.js';

export class InMemoryEventsRepo implements EventsRepo {
  private rows: EventRow[] = [];
  private alerts = new Map<string, { alert_id: string; status: any; priority: any }>();

  async seed(rows: EventRow[]): Promise<void> {
    this.rows.push(...rows);
  }

  async linkAlert(eventId: string, alert: { alert_id: string; status: any; priority: any }): Promise<void> {
    this.alerts.set(eventId, alert);
  }

  async list(f: EventFilters, limit: number, cursor?: Cursor): Promise<EventRow[]> {
    let filtered = [...this.rows];

    if (f.cameraId) {
      filtered = filtered.filter(r => r.camera_id === f.cameraId);
    }
    if (f.eventTypes && f.eventTypes.length > 0) {
      filtered = filtered.filter(r => f.eventTypes!.includes(r.event_type));
    }
    if (f.severities && f.severities.length > 0) {
      filtered = filtered.filter(r => f.severities!.includes(r.severity));
    }
    if (f.minScore !== undefined) {
      filtered = filtered.filter(r => r.threat_score >= f.minScore!);
    }
    if (f.maxScore !== undefined) {
      filtered = filtered.filter(r => r.threat_score <= f.maxScore!);
    }
    if (f.from) {
      filtered = filtered.filter(r => r.timestamp >= f.from!);
    }
    if (f.to) {
      filtered = filtered.filter(r => r.timestamp < f.to!);
    }
    if (f.trackId) {
      filtered = filtered.filter(r => r.track_id === f.trackId);
    }
    if (f.plate) {
      filtered = filtered.filter(r => r.plate === f.plate);
    }

    filtered.sort((a, b) => {
      if (a.timestamp !== b.timestamp) {
        return b.timestamp.localeCompare(a.timestamp);
      }
      return b.event_id.localeCompare(a.event_id);
    });

    if (cursor) {
      filtered = filtered.filter(r => {
        if (r.timestamp < cursor.t) return true;
        if (r.timestamp === cursor.t) return r.event_id < cursor.id;
        return false;
      });
    }

    return filtered.slice(0, limit);
  }

  async getById(id: string): Promise<{ row: EventRow; alert?: { alert_id: string; status: any; priority: any } | null } | null> {
    const row = this.rows.find(r => r.event_id === id);
    if (!row) return null;
    return {
      row,
      alert: this.alerts.get(id) ?? null,
    };
  }
}
