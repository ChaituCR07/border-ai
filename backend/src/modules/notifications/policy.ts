import { type NotificationConfig, type Priority, type Route } from './config.js';

export interface AlertCtx {
  alert_id: string;
  priority: Priority;
  created_at: string;
  camera_id: string;
  event_type: string;
  plate: string | null;
  person_related: boolean;
}

export interface LastInGroup {
  created_at_age_s: number;
  priority: Priority;
}

const PRIORITY_RANKS: Record<Priority, number> = {
  LOW: 0,
  MEDIUM: 1,
  HIGH: 2,
  CRITICAL: 3,
};

export function rank(priority: Priority): number {
  return PRIORITY_RANKS[priority] ?? 0;
}

export function normalizePlateKey(plate: string): string {
  // Normalize alphanumeric uppercase, treating common OCR look-alikes stably
  return plate
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .replace(/[OQ]/g, '0')
    .replace(/[I]/g, '1')
    .replace(/[Z]/g, '2')
    .replace(/[S]/g, '5')
    .replace(/[B]/g, '8');
}

export function groupKey(a: AlertCtx): string {
  const entityPart = a.plate ? `plate:${normalizePlateKey(a.plate)}` : `event:${a.event_type}`;
  return `${a.camera_id}|${entityPart}`;
}

export function matchRoutes(cfg: NotificationConfig, a: AlertCtx): Route[] {
  return cfg.routes.filter(r => {
    if (!r.match.priority.includes(a.priority)) {
      return false;
    }
    if (r.match.camera_id && !r.match.camera_id.includes(a.camera_id)) {
      return false;
    }
    if (r.match.event_type && !r.match.event_type.includes(a.event_type)) {
      return false;
    }
    return true;
  });
}

export type Decision = { action: 'SEND' } | { action: 'SKIP'; reason: 'cooldown' };

export function decide(
  route: Route,
  a: AlertCtx,
  last: LastInGroup | null,
  cooldownS: number
): Decision {
  // Digest routes group their own batches independently
  if (route.mode === 'digest') {
    return { action: 'SEND' };
  }

  // No previous alert in this group
  if (!last) {
    return { action: 'SEND' };
  }

  // Cooldown elapsed
  if (last.created_at_age_s >= cooldownS) {
    return { action: 'SEND' };
  }

  // Priority upgrade bypasses cooldown (e.g. HIGH -> CRITICAL)
  if (rank(a.priority) > rank(last.priority)) {
    return { action: 'SEND' };
  }

  return { action: 'SKIP', reason: 'cooldown' };
}

export function domainAllowed(recipient: string, allowedDomains: string[]): boolean {
  if (!recipient || !recipient.includes('@')) {
    return false;
  }
  const parts = recipient.trim().toLowerCase().split('@');
  if (parts.length !== 2) {
    return false;
  }
  const domain = parts[1]!;
  const normalizedAllowed = allowedDomains.map(d => d.trim().toLowerCase()).filter(Boolean);

  return normalizedAllowed.some(allowed => domain === allowed);
}

export function sanitizeHeader(val: string, maxLen = 180): string {
  return val.replace(/[\r\n]+/g, ' ').trim().slice(0, maxLen);
}

export const DEFAULT_BACKOFF_SCHEDULE_S = [10, 30, 120, 600, 1800];

export function backoffDelay(attempt: number, schedule = DEFAULT_BACKOFF_SCHEDULE_S): number {
  if (attempt <= 0) return schedule[0]!;
  const idx = Math.min(attempt - 1, schedule.length - 1);
  return schedule[idx]!;
}
