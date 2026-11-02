import React, { useEffect, useState } from 'react';

interface NotificationStatus {
  enabled: boolean;
  dry_run: boolean;
  planner: {
    running: boolean;
    is_standby: boolean;
    active: boolean;
  };
  queue: {
    pending: number;
    sending: number;
    sent: number;
    failed: number;
    cancelled: number;
    skipped: number;
  };
}

export const NotificationStatusChip: React.FC = () => {
  const [status, setStatus] = useState<NotificationStatus | null>(null);

  useEffect(() => {
    let active = true;

    const fetchStatus = () => {
      fetch('/api/notifications/status', {
        headers: { Accept: 'application/json' },
      })
        .then(async (res) => {
          if (!active) return;
          if (res.ok) {
            const json = await res.json();
            setStatus(json.data);
          } else {
            // User might not have ADMIN role or notifications disabled
            setStatus(null);
          }
        })
        .catch(() => {
          if (active) setStatus(null);
        });
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000); // 30s poll
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  if (!status) return null;

  const isStandby = status.planner.is_standby;
  const pendingCount = status.queue.pending + status.queue.sending;

  return (
    <div
      role="status"
      title={`Email Notifications: ${status.enabled ? 'Enabled' : 'Disabled'} | Planner: ${
        isStandby ? 'Standby (Passive)' : 'Active (Advisory Lock Held)'
      } | Pending: ${pendingCount} | Sent: ${status.queue.sent} | Failed: ${status.queue.failed}`}
      className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono border border-[var(--border)] bg-[var(--bg-panel-2)] text-[var(--text-muted)] cursor-default"
    >
      <span className={status.enabled ? 'text-emerald-400' : 'text-gray-400'}>✉️</span>
      <span className="font-semibold text-[var(--text)]">Outbox</span>
      {pendingCount > 0 ? (
        <span className="px-1 py-0.2 rounded bg-amber-900/60 text-amber-200 border border-amber-700/60 font-bold text-[10px]">
          {pendingCount}
        </span>
      ) : (
        <span className="text-[var(--text-dim)]">{status.queue.sent} sent</span>
      )}
      {isStandby && (
        <span className="text-[9px] uppercase px-1 rounded bg-blue-950 text-blue-300 border border-blue-800">
          Standby
        </span>
      )}
    </div>
  );
};
