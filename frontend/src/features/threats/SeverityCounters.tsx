import { SEVERITY_ORDER, getSeverityMeta } from '../../lib/severity';
import { useThreatSummary } from './useThreatSummary';
import { useUIStore } from '../../state/uiStore';

export function SeverityCounters() {
  const { data, isLoading, isError, isStale } = useThreatSummary();
  const severityFilter = useUIStore((s) => s.severityFilter);
  const setSeverityFilter = useUIStore((s) => s.setSeverityFilter);

  const openCounts = data?.open_alerts_by_priority;
  const eventCounts = data?.severity_counts;

  return (
    <section
      aria-label="Alert severity summary"
      className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 w-full select-none"
    >
      {SEVERITY_ORDER.map((sev) => {
        const meta = getSeverityMeta(sev);
        const isSelected = severityFilter === sev;
        const openVal = openCounts ? openCounts[sev] : undefined;
        const eventVal = eventCounts ? eventCounts[sev] : undefined;

        return (
          <button
            key={sev}
            type="button"
            aria-pressed={isSelected}
            aria-label={`${meta.label} alerts: ${openVal ?? 'loading'} open, ${eventVal ?? 'loading'} events in 24 hours`}
            onClick={() => setSeverityFilter(isSelected ? null : sev)}
            style={{
              borderColor: isSelected ? meta.cssVar : 'var(--border)',
              backgroundColor: isSelected ? meta.bgVar : 'var(--bg-panel)',
            }}
            className={`group relative flex flex-col justify-between p-3 rounded-[var(--radius)] border text-left transition-all cursor-pointer hover:border-[var(--border-focus)] focus:outline-none focus:ring-2 focus:ring-[var(--border-focus)] ${
              isSelected ? 'shadow-lg ring-1' : ''
            }`}
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-1.5 text-xs font-bold" style={{ color: meta.cssVar }}>
                <span aria-hidden="true">{meta.icon}</span>
                <span className="tracking-wide uppercase">{meta.label}</span>
              </div>
              {sev === 'CRITICAL' && openVal && openVal > 0 && (
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--sev-critical)] opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--sev-critical)]" />
                </span>
              )}
            </div>

            <div className="my-1.5 flex items-baseline gap-2">
              <span
                data-testid={`count-${sev}`}
                className="text-3xl font-extrabold tracking-tight font-mono text-[var(--text)]"
              >
                {isLoading || openVal === undefined ? '–' : openVal}
              </span>
              <span className="text-xs font-semibold text-[var(--text-muted)]">open</span>
            </div>

            <div className="flex items-center justify-between text-[11px] text-[var(--text-dim)] border-t border-[var(--border-muted)] pt-1.5 mt-0.5">
              <span>
                {isLoading || eventVal === undefined ? '–' : eventVal} in 24h
              </span>
              {(isStale || isError) && (
                <span className="text-[10px] text-[var(--warn)] font-medium">stale</span>
              )}
            </div>
          </button>
        );
      })}
    </section>
  );
}
