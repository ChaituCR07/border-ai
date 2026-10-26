import { useRecentEvents } from './useRecentEvents';
import { getSeverityMeta } from '../../lib/severity';
import { formatTime, relativeTime } from '../../lib/time';
import { formatPlate } from '../../lib/plate';
import { useUIStore } from '../../state/uiStore';

export function RecentEvents() {
  const { data: events, isLoading, isError } = useRecentEvents(8);
  const tzMode = useUIStore((s) => s.tzMode);
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);
  const selectedCameraId = useUIStore((s) => s.selectedCameraId);

  return (
    <div className="flex flex-col h-full bg-[var(--bg-panel)] rounded-[var(--radius)] border border-[var(--border)] overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] bg-[var(--bg-panel-2)]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
            Recent Intelligence Events
          </span>
          <span className="text-[10px] text-[var(--text-dim)]">(Last 8 detections)</span>
        </div>
        <span className="text-[11px] font-mono text-[var(--text-dim)]">Live Poll · 10s</span>
      </div>

      <div className="flex-1 overflow-x-auto overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-[var(--border)] text-[10px] uppercase font-semibold text-[var(--text-dim)] bg-[var(--bg-app)]">
              <th className="py-1.5 px-3">Time</th>
              <th className="py-1.5 px-2">Camera</th>
              <th className="py-1.5 px-2">Classification</th>
              <th className="py-1.5 px-2">Severity</th>
              <th className="py-1.5 px-2">Plate</th>
              <th className="py-1.5 px-3 text-right">Threat</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-muted)]">
            {isLoading && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-xs text-[var(--text-dim)]">
                  Loading intelligence events stream...
                </td>
              </tr>
            )}

            {isError && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-xs text-[var(--sev-critical)]">
                  Unable to fetch recent events. Retrying...
                </td>
              </tr>
            )}

            {!isLoading && (!events || events.length === 0) && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-xs text-[var(--text-dim)]">
                  No detection events recorded in current time window.
                </td>
              </tr>
            )}

            {events?.map((ev) => {
              const meta = getSeverityMeta(ev.severity);
              const isSelected = ev.camera_id === selectedCameraId;

              return (
                <tr
                  key={ev.event_id}
                  tabIndex={0}
                  onClick={() => setSelectedCamera(ev.camera_id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedCamera(ev.camera_id);
                    }
                  }}
                  className={`hover:bg-[var(--bg-panel-2)] cursor-pointer transition-colors focus:bg-[var(--bg-panel-2)] focus:outline-none ${
                    isSelected ? 'bg-[var(--bg-panel-2)]/80 font-medium' : ''
                  }`}
                >
                  <td className="py-1.5 px-3 font-mono text-[11px] text-[var(--text-muted)] whitespace-nowrap">
                    <span title={formatTime(ev.timestamp, tzMode)}>
                      {relativeTime(ev.timestamp)}
                    </span>
                  </td>

                  <td className="py-1.5 px-2 font-mono font-bold text-[var(--text)] whitespace-nowrap">
                    {ev.camera_id}
                  </td>

                  <td className="py-1.5 px-2 text-[var(--text)] whitespace-nowrap">
                    {ev.event_type.replace(/_/g, ' ')}
                  </td>

                  <td className="py-1.5 px-2 whitespace-nowrap">
                    <span
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border"
                      style={{
                        backgroundColor: meta.bgVar,
                        borderColor: meta.cssVar,
                        color: meta.cssVar,
                      }}
                    >
                      <span aria-hidden="true">{meta.icon}</span>
                      <span>{meta.label}</span>
                    </span>
                  </td>

                  <td className="py-1.5 px-2 font-mono text-xs text-[var(--text-muted)] whitespace-nowrap">
                    {ev.plate ? (
                      <span className="font-semibold text-[var(--text)]">
                        {formatPlate(ev.plate)}
                      </span>
                    ) : (
                      '–'
                    )}
                  </td>

                  <td className="py-1.5 px-3 text-right font-mono font-bold text-xs whitespace-nowrap">
                    <span
                      style={{
                        color:
                          ev.threat_score >= 80
                            ? 'var(--sev-critical)'
                            : ev.threat_score >= 60
                            ? 'var(--sev-high)'
                            : ev.threat_score >= 40
                            ? 'var(--sev-medium)'
                            : 'var(--sev-low)',
                      }}
                    >
                      {ev.threat_score}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
