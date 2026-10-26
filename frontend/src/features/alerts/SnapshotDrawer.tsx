import { useEffect } from 'react';
import type { AlertResource } from '../../api/types';
import { getSeverityMeta } from '../../lib/severity';
import { formatTime, relativeTime } from '../../lib/time';
import { formatPlate } from '../../lib/plate';
import { useUIStore } from '../../state/uiStore';

interface SnapshotDrawerProps {
  alert: AlertResource;
  onClose: () => void;
}

export function SnapshotDrawer({ alert, onClose }: SnapshotDrawerProps) {
  const meta = getSeverityMeta(alert.priority);
  const tzMode = useUIStore((s) => s.tzMode);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

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

            <div className="flex justify-between py-1">
              <span className="text-[var(--text-dim)]">Status</span>
              <span className="font-semibold text-[var(--warn)] uppercase">{alert.status}</span>
            </div>
          </div>
        </div>

        <footer className="mt-4 pt-3 border-t border-[var(--border)] text-[11px] text-[var(--text-dim)] text-center leading-relaxed">
          Contains personal data / license plate evidence. Access logged and audited per Border Intelligence security policy.
        </footer>
      </div>
    </div>
  );
}
