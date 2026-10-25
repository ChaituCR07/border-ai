import type { AlertsRepo, AlertFilters } from './repo.js';
import type { AlertResource } from '../../types/domain.js';
import type { Cursor } from '../../common/pagination.js';

export class InMemoryAlertsRepo implements AlertsRepo {
  private alerts: AlertResource[] = [];

  async seed(items: AlertResource[]): Promise<void> {
    this.alerts.push(...items);
  }

  async list(f: AlertFilters, limit: number, cursor?: Cursor): Promise<AlertResource[]> {
    let filtered = [...this.alerts];

    if (f.status) {
      filtered = filtered.filter(a => a.status === f.status);
    }
    if (f.priority) {
      filtered = filtered.filter(a => a.priority === f.priority);
    }
    if (f.cameraId) {
      filtered = filtered.filter(a => a.event.camera_id === f.cameraId);
    }
    if (f.from) {
      filtered = filtered.filter(a => a.created_at >= f.from!);
    }
    if (f.to) {
      filtered = filtered.filter(a => a.created_at < f.to!);
    }

    filtered.sort((a, b) => {
      if (a.created_at !== b.created_at) {
        return b.created_at.localeCompare(a.created_at);
      }
      return b.alert_id.localeCompare(a.alert_id);
    });

    if (cursor) {
      filtered = filtered.filter(a => {
        if (a.created_at < cursor.t) return true;
        if (a.created_at === cursor.t) return a.alert_id < cursor.id;
        return false;
      });
    }

    return filtered.slice(0, limit);
  }

  async getById(alertId: string): Promise<AlertResource | null> {
    return this.alerts.find(a => a.alert_id === alertId) ?? null;
  }

  async acknowledge(alertId: string, acknowledgedBy: string): Promise<{ alert: AlertResource; updated: boolean } | null> {
    const existing = this.alerts.find(a => a.alert_id === alertId);
    if (!existing) return null;

    if (existing.status === 'OPEN') {
      existing.status = 'ACKNOWLEDGED';
      existing.acknowledged_by = acknowledgedBy;
      existing.acknowledged_at = new Date().toISOString();
      return { alert: existing, updated: true };
    }

    return { alert: existing, updated: false };
  }
}
