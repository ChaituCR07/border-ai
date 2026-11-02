import { useEffect, useState } from 'react';
import type { AlertResource } from '../../api/types';
import { getSeverityMeta } from '../../lib/severity';
import { formatTime, relativeTime } from '../../lib/time';
import { formatPlate } from '../../lib/plate';
import { useUIStore } from '../../state/uiStore';
import { ResolveDialog, type ResolutionChoice } from './ResolveDialog';

interface AlertDetailExtended extends AlertResource {
  notifications?: {
    total: number;
    sent: number;
    pending: number;
    failed: number;
    cancelled: number;
  };
  explanation?: { factors?: Array<{ name: string; points: number }> } | null;
  resolution_note?: string | null;
}

interface SnapshotDrawerProps {
  alert: AlertResource;
  onClose: () => void;
}

export function SnapshotDrawer({ alert: initialAlert, onClose }: SnapshotDrawerProps) {
  const [alert, setAlert] = useState<AlertDetailExtended>(initialAlert);
  const [isResolveOpen, setIsResolveOpen] = useState(false);
  const meta = getSeverityMeta(alert.priority);
  const tzMode = useUIStore((s) => s.tzMode);

  // Fetch full detail with notifications & explanation
  useEffect(() => {
    let active = true;
    fetch(`/api/alerts/${encodeURIComponent(initialAlert.alert_id)}`, {
      headers: { Accept: 'application/json' },
    })
      .then(async (res) => {
        if (!active) return;
        if (res.ok) {
          const json = await res.json();
          setAlert((prev) => ({ ...prev, ...json.data }));
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [initialAlert.alert_id]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isResolveOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, isResolveOpen]);

  const handleResolved = (resolution: ResolutionChoice, note?: string) => {
    setAlert((prev) => ({
      ...prev,
      status: 'RESOLVED',
      resolution,
      resolution_note: note || null,
      resolved_at: new Date().toISOString(),
      resolved_by: 'current-user',
    }));
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-xs transition-opacity"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md h-full bg-[var(--bg-panel)] border-l border-[var(--border)] p-5 flex flex-col shadow-2xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)] mb-4">
          <div className="flex items-center gap-2">
            <span
              className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold border"
              style={{
                backgroundColor: meta.bgVar,
                borderColor: meta.cssVar,
                color: meta.cssVar,
              }}
            >
              <span>{meta.icon}</span>
              <span>{meta.label}</span>
            </span>
            <h2 id="drawer-title" className="text-sm font-bold text-[var(--text)]">
              Evidence Snapshot
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close drawer"
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-[var(--bg-app)] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 flex flex-col gap-4">
          <figure className="relative aspect-video rounded-[var(--radius)] overflow-hidden bg-black border border-[var(--border)] flex items-center justify-center">
            {alert.event.snapshot_url ? (
              <img
                src={alert.event.snapshot_url}
                alt={`Evidence snapshot for alert on ${alert.event.camera_id}`}
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            ) : (
              <div className="text-center p-4 text-xs text-[var(--text-dim)]">
                <span className="block text-2xl mb-1">📷</span>
                Snapshot no longer available on disk (retention policy)
              </div>
            )}
          </figure>

          <div className="space-y-3 bg-[var(--bg-panel-2)] p-4 rounded-[var(--radius)] border border-[var(--border)] text-xs">
            <div className="flex justify-between py-1 border-b border-[var(--border-muted)]">
              <span className="text-[var(--text-dim)]">Camera</span>
              <span className="font-mono font-bold text-[var(--text)]">{alert.event.camera_id}</span>
            </div>

            <div className="flex justify-between py-1 border-b border-[var(--border-muted)]">
              <span className="text-[var(--text-dim)]">Event Type</span>
              <span className="font-semibold text-[var(--text)]">
                {alert.event.event_type.replace(/_/g, ' ')}
              </span>
            </div>

            <div className="flex justify-between py-1 border-b border-[var(--border-muted)]">
              <span className="text-[var(--text-dim)]">Threat Score</span>
              <span className="font-mono font-bold text-[var(--sev-critical)]">
                {alert.event.threat_score} / 100
              </span>
            </div>

            {alert.event.plate && (
              <div className="flex justify-between py-1 border-b border-[var(--border-muted)]">
                <span className="text-[var(--text-dim)]">License Plate</span>
                <span className="font-mono font-bold text-[var(--text)]">
                  {formatPlate(alert.event.plate)}
                </span>
              </div>
            )}

            <div className="flex justify-between py-1 border-b border-[var(--border-muted)]">
              <span className="text-[var(--text-dim)]">Timestamp</span>
              <span className="font-mono text-[var(--text)]">
                {formatTime(alert.created_at, tzMode)} ({relativeTime(alert.created_at)})
              </span>
            </div>

            <div className="flex justify-between py-1 border-b border-[var(--border-muted)]">
              <span className="text-[var(--text-dim)]">Status</span>
              <span
                className={`font-semibold uppercase ${
                  alert.status === 'RESOLVED'
                    ? 'text-[var(--ok)]'
                    : alert.status === 'ACKNOWLEDGED'
                    ? 'text-cyan-400'
                    : 'text-[var(--warn)]'
                }`}
              >
                {alert.status}
              </span>
            </div>

            {alert.status === 'RESOLVED' && (
              <div className="py-2 border-b border-[var(--border-muted)] space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-[var(--text-dim)]">Resolution</span>
                  <span className="font-semibold text-emerald-300">{alert.resolution}</span>
                </div>
                {alert.resolved_by && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[var(--text-dim)]">Resolved By</span>
                    <span className="font-mono text-[var(--text)]">{alert.resolved_by}</span>
                  </div>
                )}
                {alert.resolved_at && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[var(--text-dim)]">Resolved At</span>
                    <span className="font-mono text-[var(--text)]">
                      {formatTime(alert.resolved_at, tzMode)}
                    </span>
                  </div>
                )}
                {alert.resolution_note && (
                  <div className="mt-1 p-2 rounded bg-[var(--bg-app)] border border-[var(--border-muted)] text-[11px] text-[var(--text-muted)] italic">
                    "{alert.resolution_note}"
                  </div>
                )}
              </div>
            )}

            {alert.explanation?.factors && alert.explanation.factors.length > 0 && (
              <div className="py-2 border-b border-[var(--border-muted)] space-y-1.5">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  Threat Factor Breakdown
                </span>
                <div className="space-y-1">
                  {alert.explanation.factors.map((f, i) => (
                    <div key={i} className="flex justify-between text-[11px]">
                      <span className="text-[var(--text)]">{f.name.replace(/_/g, ' ')}</span>
                      <span className="font-mono text-[var(--warn)]">+{f.points} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {alert.notifications && alert.notifications.total > 0 && (
              <div className="py-2 border-b border-[var(--border-muted)] space-y-1">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  Email Dispatch Outbox
                </span>
                <div className="flex items-center gap-2 pt-1">
                  <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800 text-[10px] font-mono">
                    Sent: {alert.notifications.sent}
                  </span>
                  {alert.notifications.pending > 0 && (
                    <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800 text-[10px] font-mono">
                      Pending: {alert.notifications.pending}
                    </span>
                  )}
                  {alert.notifications.failed > 0 && (
                    <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800 text-[10px] font-mono">
                      Failed: {alert.notifications.failed}
                    </span>
                  )}
                  {alert.notifications.cancelled > 0 && (
                    <span className="px-2 py-0.5 rounded bg-gray-900 text-gray-400 border border-gray-700 text-[10px] font-mono">
                      Cancelled: {alert.notifications.cancelled}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {alert.status !== 'RESOLVED' && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setIsResolveOpen(true)}
                className="w-full py-2 px-3 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-xs cursor-pointer transition-colors shadow-sm flex items-center justify-center gap-1.5"
              >
                <span>✓</span>
                <span>Resolve Alert...</span>
              </button>
            </div>
          )}
        </div>

        <footer className="mt-4 pt-3 border-t border-[var(--border)] text-[11px] text-[var(--text-dim)] text-center leading-relaxed">
          Contains personal data / license plate evidence. Access logged and audited per Border Intelligence security policy.
        </footer>
      </div>

      <ResolveDialog
        alertId={alert.alert_id}
        isOpen={isResolveOpen}
        onClose={() => setIsResolveOpen(false)}
        onResolved={handleResolved}
      />
    </div>
  );
}
