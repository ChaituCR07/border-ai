import type { InvestigationRepo, FacetResult, SuggestItem, EventContextResult } from './repo.js';
import type { EventFilters, EventRow } from '../events/repo.js';
import type { InMemoryEventsRepo } from '../events/repo.memory.js';
import { plateNorm, plateKey, type PlateMatch } from '../../common/plate.js';

export class InMemoryInvestigationRepo implements InvestigationRepo {
  private events: EventRow[] = [];
  private alerts = new Map<string, { alert_id: string; status: any; priority: any }>();

  constructor(private readonly eventsRepo?: InMemoryEventsRepo) {}

  async seed(rows: EventRow[]): Promise<void> {
    this.events.push(...rows);
  }

  async linkAlert(eventId: string, alert: { alert_id: string; status: any; priority: any }): Promise<void> {
    this.alerts.set(eventId, alert);
  }

  private filterList(events: EventRow[], f: EventFilters): EventRow[] {
    let res = [...events];
    if (f.eventId) res = res.filter(r => r.event_id === f.eventId);
    if (f.cameraId) res = res.filter(r => r.camera_id === f.cameraId);
    if (f.cameraIds && f.cameraIds.length > 0) res = res.filter(r => f.cameraIds!.includes(r.camera_id));
    if (f.eventTypes && f.eventTypes.length > 0) res = res.filter(r => f.eventTypes!.includes(r.event_type));
    if (f.severities && f.severities.length > 0) res = res.filter(r => f.severities!.includes(r.severity));
    if (f.minScore !== undefined) res = res.filter(r => r.threat_score >= f.minScore!);
    if (f.maxScore !== undefined) res = res.filter(r => r.threat_score <= f.maxScore!);
    if (f.from) res = res.filter(r => r.timestamp >= f.from!);
    if (f.to) res = res.filter(r => r.timestamp < f.to!);
    if (f.trackId) res = res.filter(r => r.track_id === f.trackId);
    if (f.vehicleId) res = res.filter(r => r.vehicle_id === f.vehicleId || r.metadata?.vehicle_id === f.vehicleId);
    if (f.personId) res = res.filter(r => (
      r.person_id === f.personId ||
      r.metadata?.person_id === f.personId ||
      r.metadata?.reid_candidate_id === f.personId ||
      r.metadata?.subject_id === f.personId
    ));

    if (f.plate) {
      const mode = (f.plateMatch ?? 'lookalike') as PlateMatch;
      const targetNorm = plateNorm(f.plate);
      const targetKey = plateKey(f.plate);

      res = res.filter(r => {
        const candidate = r.plate ?? (r.metadata?.plate as string) ?? '';
        const candNorm = plateNorm(candidate);
        if (!candNorm) return false;
        if (mode === 'exact') return candNorm === targetNorm;
        if (mode === 'prefix') return candNorm.startsWith(targetNorm);
        if (mode === 'contains') return candNorm.includes(targetNorm);
        return candNorm === targetNorm || plateKey(candidate) === targetKey;
      });
    }

    if (f.timeFrom && f.timeTo) {
      const tz = f.tz || 'UTC';
      res = res.filter(r => {
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

    return res;
  }

  async getFacets(filters: EventFilters): Promise<FacetResult> {
    const matching = this.filterList(this.events, filters);

    // Disjunctive: by_camera ignores camera filter
    const camFilters = { ...filters, cameraId: undefined, cameraIds: undefined };
    const camEvents = this.filterList(this.events, camFilters);
    const camMap = new Map<string, number>();
    camEvents.forEach(e => camMap.set(e.camera_id, (camMap.get(e.camera_id) ?? 0) + 1));
    const by_camera = Array.from(camMap.entries())
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count);

    // Disjunctive: by_event_type ignores event_type filter
    const typeFilters = { ...filters, eventTypes: undefined };
    const typeEvents = this.filterList(this.events, typeFilters);
    const typeMap = new Map<string, number>();
    typeEvents.forEach(e => typeMap.set(e.event_type, (typeMap.get(e.event_type) ?? 0) + 1));
    const by_event_type = Array.from(typeMap.entries())
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count);

    // Disjunctive: by_severity ignores severity filter
    const sevFilters = { ...filters, severities: undefined };
    const sevEvents = this.filterList(this.events, sevFilters);
    const by_severity = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    sevEvents.forEach(e => {
      if (e.severity in by_severity) {
        by_severity[e.severity]++;
      }
    });

    // Score histogram (0..9, 10..19, ..., 90..100)
    const scoreBuckets = Array.from({ length: 10 }, (_, i) => ({
      from: i * 10,
      to: i === 9 ? 100 : i * 10 + 9,
      count: 0,
    }));
    matching.forEach(e => {
      const idx = Math.min(Math.floor(e.threat_score / 10), 9);
      scoreBuckets[idx]!.count++;
    });

    // Hours histogram (0..23)
    const hourBuckets = Array.from({ length: 24 }, (_, hour) => ({
      hour,
      count: 0,
    }));
    matching.forEach(e => {
      const h = new Date(e.timestamp).getUTCHours();
      if (h >= 0 && h < 24) {
        hourBuckets[h]!.count++;
      }
    });

    return {
      total: matching.length,
      by_camera,
      by_event_type,
      by_severity,
      score_histogram: scoreBuckets,
      hours: hourBuckets,
      capped: false,
    };
  }

  async suggest(kind: 'plate' | 'camera' | 'person', prefix: string, limit = 10): Promise<SuggestItem[]> {
    const normPre = prefix.toUpperCase().trim();
    if (kind === 'camera') {
      const camMap = new Map<string, { count: number; last_seen: string }>();
      this.events.forEach(e => {
        if (e.camera_id.toUpperCase().startsWith(normPre)) {
          const cur = camMap.get(e.camera_id);
          camMap.set(e.camera_id, {
            count: (cur?.count ?? 0) + 1,
            last_seen: cur && cur.last_seen > e.timestamp ? cur.last_seen : e.timestamp,
          });
        }
      });
      return Array.from(camMap.entries())
        .map(([value, info]) => ({ value, ...info }))
        .sort((a, b) => b.last_seen.localeCompare(a.last_seen))
        .slice(0, limit);
    }

    if (kind === 'person') {
      const personMap = new Map<string, { count: number; last_seen: string }>();
      this.events.forEach(e => {
        const pid = e.person_id ?? (e.metadata?.person_id as string);
        if (pid && pid.toUpperCase().startsWith(normPre)) {
          const cur = personMap.get(pid);
          personMap.set(pid, {
            count: (cur?.count ?? 0) + 1,
            last_seen: cur && cur.last_seen > e.timestamp ? cur.last_seen : e.timestamp,
          });
        }
      });
      return Array.from(personMap.entries())
        .map(([value, info]) => ({ value, ...info }))
        .sort((a, b) => b.last_seen.localeCompare(a.last_seen))
        .slice(0, limit);
    }

    // Plate suggest
    const plateMap = new Map<string, { count: number; last_seen: string }>();
    this.events.forEach(e => {
      const p = e.plate ?? (e.metadata?.plate as string);
      if (p) {
        const norm = plateNorm(p);
        if (norm.startsWith(normPre)) {
          const cur = plateMap.get(norm);
          plateMap.set(norm, {
            count: (cur?.count ?? 0) + 1,
            last_seen: cur && cur.last_seen > e.timestamp ? cur.last_seen : e.timestamp,
          });
        }
      }
    });
    return Array.from(plateMap.entries())
      .map(([value, info]) => ({ value, ...info }))
      .sort((a, b) => b.last_seen.localeCompare(a.last_seen))
      .slice(0, limit);
  }

  async getEventContext(eventId: string, windowSeconds = 60): Promise<EventContextResult | null> {
    const event = this.events.find(e => e.event_id === eventId);
    if (!event) return null;

    const t = new Date(event.timestamp).getTime();
    const windowMs = windowSeconds * 1000;
    const fifteenMinMs = 15 * 60 * 1000;

    const same_camera_around = this.events
      .filter(e => e.event_id !== eventId && e.camera_id === event.camera_id)
      .filter(e => Math.abs(new Date(e.timestamp).getTime() - t) <= windowMs)
      .slice(0, 50);

    const plate = event.plate ? plateNorm(event.plate) : null;
    const same_subject_elsewhere = this.events
      .filter(e => e.event_id !== eventId && e.camera_id !== event.camera_id)
      .filter(e => {
        const candPlate = e.plate ? plateNorm(e.plate) : null;
        const matchesPlate = plate && candPlate && (plate === candPlate || plateKey(plate) === plateKey(candPlate));
        const matchesVehicle = event.vehicle_id && e.vehicle_id && event.vehicle_id === e.vehicle_id;
        return matchesPlate || matchesVehicle;
      })
      .filter(e => Math.abs(new Date(e.timestamp).getTime() - t) <= fifteenMinMs)
      .slice(0, 50);

    return {
      event,
      same_camera_around,
      same_subject_elsewhere,
      alert: this.alerts.get(eventId) ?? null,
    };
  }

  async getJourneyEvents(filter: { plate?: string; vehicleId?: string; from?: string; to?: string }): Promise<EventRow[]> {
    let res = [...this.events];
    if (filter.from) res = res.filter(r => r.timestamp >= filter.from!);
    if (filter.to) res = res.filter(r => r.timestamp < filter.to!);

    if (filter.vehicleId) {
      res = res.filter(r => r.vehicle_id === filter.vehicleId || r.metadata?.vehicle_id === filter.vehicleId);
    } else if (filter.plate) {
      const targetNorm = plateNorm(filter.plate);
      const targetKey = plateKey(filter.plate);
      res = res.filter(r => {
        const candidate = r.plate ?? (r.metadata?.plate as string) ?? '';
        const candNorm = plateNorm(candidate);
        if (!candNorm) return false;
        return candNorm === targetNorm || plateKey(candidate) === targetKey;
      });
    }

    res.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    return res.slice(0, 5000);
  }
}
