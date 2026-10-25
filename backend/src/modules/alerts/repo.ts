import type { AlertResource, AlertStatus, Severity } from '../../types/domain.js';
import type { Cursor } from '../../common/pagination.js';

export interface AlertFilters {
  status?: AlertStatus;
  priority?: Severity;
  cameraId?: string;
  from?: string;
  to?: string;
}

export interface AlertsRepo {
  list(filters: AlertFilters, limit: number, cursor?: Cursor): Promise<AlertResource[]>;
  getById(alertId: string): Promise<AlertResource | null>;
  acknowledge(alertId: string, acknowledgedBy: string): Promise<{ alert: AlertResource; updated: boolean } | null>;
}
