import { useState } from 'react';
import { useOpenAlerts } from './useOpenAlerts';
import { AlertCard } from './AlertCard';
import { SnapshotDrawer } from './SnapshotDrawer';
import type { AlertResource } from '../../api/types';
import { useUIStore } from '../../state/uiStore';
import { getSeverityMeta } from '../../lib/severity';

export function AlertFeed() {
  const { alerts, counts, transport, isStale } = useOpenAlerts();
  const severityFilter = useUIStore((s) => s.severityFilter);
  const setSeverityFilter = useUIStore((s) => s.setSeverityFilter);
  const selectedCameraId = useUIStore((s) => s.selectedCameraId);
  const selectedCameraOnly = useUIStore((s) => s.selectedCameraOnly);
  const toggleSelectedCameraOnly = useUIStore((s) => s.toggleSelectedCameraOnly);

  const [selectedAlertForSnapshot, setSelectedAlertForSnapshot] = useState<AlertResource | null>(null);

  const totalOpen = alerts.length;

  return (
    <aside
      aria-label="Open alerts feed"
      className="w-80 md:w-96 border-l border-[var(--border)] bg-[var(--bg-panel)] flex flex-col shrink-0 h-full overflow-hidden select-none"
    >
      <div className="p-3 border-b border-[var(--border)]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
              Open Alerts
            </h2>
            <span className="font-mono text-xs px-2 py-0.5 rounded-full font-bold bg-[var(--bg-app)] text-[var(--text)] border border-[var(--border)]">
              {totalOpen}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-[10px] text-[var(--text-dim)]">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                transport === 'websocket' ? 'bg-[var(--ok)]' : 'bg-[var(--warn)]'
              }`}
            />
            <span className="uppercase">{transport}</span>
            {isStale && <span className="text-[var(--warn)] font-bold ml-1">(stale)</span>}
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          {severityFilter && (
            <button
              onClick={() => setSeverityFilter(null)}
              className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-[var(--bg-app)] border border-[var(--border-focus)] text-[var(--text)] hover:opacity-80 cursor-pointer"
            >
              <span>{getSeverityMeta(severityFilter).icon}</span>
              <span>{severityFilter}</span>
              <span className="text-[var(--text-dim)] ml-1">✕</span>
            </button>
          )}

          <button
            type="button"
            onClick={toggleSelectedCameraOnly}
            className={`text-[11px] px-2 py-0.5 rounded border transition-colors cursor-pointer ${
              selectedCameraOnly
                ? 'bg-[var(--border-focus)] border-[var(--border-focus)] text-white'
                : 'bg-[var(--bg-app)] border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)]'
            }`}
          >
            {selectedCameraOnly && selectedCameraId ? `Only ${selectedCameraId}` : 'This Camera Only'}
          </button>
        </div>
      </div>

      <div
        role="feed"
        aria-busy={false}
        className="flex-1 overflow-y-auto p-3 space-y-2.5"
      >
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center h-full">
            <span className="text-3xl mb-2 text-[var(--ok)]">✓</span>
            <h3 className="text-sm font-semibold text-[var(--text)]">All Clear</h3>
            <p className="text-xs text-[var(--text-dim)] mt-1 max-w-[200px]">
              {severityFilter || selectedCameraOnly
                ? 'No alerts match current active filter criteria.'
                : 'No unacknowledged high threat alerts in queue.'}
            </p>
          </div>
        ) : (
          alerts.map((alert) => (
            <AlertCard
              key={alert.alert_id}
              alert={alert}
              onViewSnapshot={(a) => setSelectedAlertForSnapshot(a)}
            />
          ))
        )}
      </div>

      {selectedAlertForSnapshot && (
        <SnapshotDrawer
          alert={selectedAlertForSnapshot}
          onClose={() => setSelectedAlertForSnapshot(null)}
        />
      )}
    </aside>
  );
}
