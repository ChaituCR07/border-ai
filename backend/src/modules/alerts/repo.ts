import type { AlertResource, AlertStatus, Severity } from '../../types/domain.js';
import type { Cursor } from '../../common/pagination.js';

export interface AlertFilters {
  status?: AlertStatus;
  priority?: Severity;
  cameraId?: string;
  from?: string;
  to?: string;
}

export interface ResolveParams {
  resolvedBy: string;
  resolution: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'DUPLICATE' | 'OTHER';
  note?: string;
}

export interface NotificationSummary {
  sent: number;
  pending: number;
  skipped: number;
  failed: number;
  items?: Array<{
    notification_id: string;
    kind: string;
    recipient: string;
    status: string;
    sent_at?: string | null;
  }>;
}

export interface AlertDetailResult extends AlertResource {
  explanation?: Array<{ name: string; points: number; detail?: string }>;
  notifications: NotificationSummary;
}

export interface AlertsRepo {
  list(filters: AlertFilters, limit: number, cursor?: Cursor): Promise<AlertResource[]>;
  getById(alertId: string): Promise<AlertResource | null>;
  acknowledge(alertId: string, acknowledgedBy: string): Promise<{ alert: AlertResource; updated: boolean } | null>;
  resolve(alertId: string, params: ResolveParams): Promise<{ alert: AlertResource; updated: boolean } | null>;
  getNotificationSummary(alertId: string, isAdmin: boolean): Promise<NotificationSummary>;
  getExplanation(eventId: string): Promise<Array<{ name: string; points: number; detail?: string }> | null>;
}
