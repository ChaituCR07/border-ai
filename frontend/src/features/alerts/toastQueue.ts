import type { AlertView } from '@border-ai/protocol';

export interface Toast {
  id: string; // alert_id of representative alert
  alert: AlertView;
  count: number; // coalesced alert count
  createdAt: number;
  expiresAt: number | null; // null = sticky (CRITICAL)
  groupKey: string;
}

export const groupKeyOf = (a: AlertView) => `${a.event.camera_id}|${a.event.plate ?? a.event.event_type}`;

export const WINDOW_MS = 20_000;
export const MAX_VISIBLE = 3;

const severityRank: Record<string, number> = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1,
};

export const rank = (priority: string) => severityRank[priority] ?? 0;

export function enqueue(toasts: Toast[], alert: AlertView, now: number): Toast[] {
  // ADR 0021: MEDIUM / LOW never produce toasts
  if (alert.priority === 'MEDIUM' || alert.priority === 'LOW') {
    return toasts;
  }

  const key = groupKeyOf(alert);
  const existing = toasts.find(t => t.groupKey === key && now - t.createdAt <= WINDOW_MS);

  if (existing) {
    const stronger = alert.event.threat_score > existing.alert.event.threat_score;
    return toasts.map(t =>
      t === existing
        ? {
            ...t,
            count: t.count + 1,
            alert: stronger ? alert : t.alert,
            id: stronger ? alert.alert_id : t.id,
            expiresAt:
              existing.expiresAt === null || alert.priority === 'CRITICAL'
                ? null
                : Math.max(existing.expiresAt, now + 15_000),
          }
        : t
    );
  }

  const t: Toast = {
    id: alert.alert_id,
    alert,
    count: 1,
    createdAt: now,
    groupKey: key,
    expiresAt: alert.priority === 'CRITICAL' ? null : now + 15_000,
  };

  return [t, ...toasts].sort(
    (a, b) => rank(b.alert.priority) - rank(a.alert.priority) || b.createdAt - a.createdAt
  );
}

export const dismissById = (ts: Toast[], id: string): Toast[] => ts.filter(t => t.id !== id);

export const expire = (ts: Toast[], now: number): Toast[] =>
  ts.filter(t => t.expiresAt === null || t.expiresAt > now);

export const visible = (ts: Toast[]) => ({
  shown: ts.slice(0, MAX_VISIBLE),
  hidden: Math.max(0, ts.length - MAX_VISIBLE),
});
