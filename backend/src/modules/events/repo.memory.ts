import type { EventsRepo, EventFilters, EventRow } from './repo.js';
import type { Cursor } from '../../common/pagination.js';
import { classifyPlateMatch, type PlateMatch } from '../../common/plate.js';

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

    if (f.eventId) {
      filtered = filtered.filter(r => r.event_id === f.eventId);
    }
    if (f.cameraId) {
      filtered = filtered.filter(r => r.camera_id === f.cameraId);
    }
    if (f.cameraIds && f.cameraIds.length > 0) {
      filtered = filtered.filter(r => f.cameraIds!.includes(r.camera_id));
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
    if (f.vehicleId) {
      filtered = filtered.filter(r => (r.vehicle_id === f.vehicleId || r.metadata?.vehicle_id === f.vehicleId));
    }
    if (f.personId) {
      filtered = filtered.filter(r => (
        r.person_id === f.personId ||
        r.metadata?.person_id === f.personId ||
        r.metadata?.reid_candidate_id === f.personId ||
        r.metadata?.subject_id === f.personId
      ));
    }

    if (f.plate) {
      const mode = (f.plateMatch ?? 'lookalike') as PlateMatch;
      filtered = filtered.flatMap(r => {
        const candidate = r.plate ?? (r.metadata?.plate as string) ?? '';
        const match = classifyPlateMatch(f.plate!, candidate, mode);
        if (match === 'none') return [];
        return [{
          ...r,
          plate_match: match,
        }];
      });
    }

    if (f.timeFrom && f.timeTo) {
      const tz = f.tz || 'UTC';
      filtered = filtered.filter(r => {
        try {
          const date = new Date(r.timestamp);
          const timeParts = date.toLocaleTimeString('en-GB', {
            timeZone: tz,
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
          });
          if (f.timeFrom! <= f.timeTo!) {
            return timeParts >= f.timeFrom! && timeParts < f.timeTo!;
          } else {
            return timeParts >= f.timeFrom! || timeParts < f.timeTo!;
          }
        } catch {
          return true;
        }
      });
    }

    // Sort order
    if (f.sort === 'score') {
      filtered.sort((a, b) => {
        if (a.threat_score !== b.threat_score) {
          return b.threat_score - a.threat_score;
        }
        if (a.timestamp !== b.timestamp) {
          return b.timestamp.localeCompare(a.timestamp);
        }
        return b.event_id.localeCompare(a.event_id);
      });

      if (cursor && cursor.score !== undefined) {
        filtered = filtered.filter(r => {
          if (r.threat_score < cursor.score!) return true;
          if (r.threat_score === cursor.score!) {
            if (r.timestamp < cursor.t) return true;
            if (r.timestamp === cursor.t) return r.event_id < cursor.id;
          }
          return false;
        });
      }
    } else {
      // Default: sort = 'time'
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
