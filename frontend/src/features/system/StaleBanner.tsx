import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';
import { formatTime } from '../../lib/time';
import { useUIStore } from '../../state/uiStore';
import { useLiveAlertsContext } from '../alerts/LiveAlertsProvider';

export function StaleBanner() {
  const tzMode = useUIStore((s) => s.tzMode);

  const { data, isError, dataUpdatedAt } = useQuery({
    queryKey: keys.ready,
    queryFn: () => unwrap(api.GET('/api/ready') as any) as Promise<{ status?: string }>,
    refetchInterval: POLL_INTERVALS.HEALTH,
    retry: 1,
  });

  let resyncBannerCount: number | null = null;
  let clearResyncBanner = () => {};

  try {
    const live = useLiveAlertsContext();
    resyncBannerCount = live.resyncBannerCount;
    clearResyncBanner = live.clearResyncBanner;
  } catch {
    // Context fallback
  }

  const isOffline = isError || (data && data.status !== 'ready');

  if (isOffline) {
    return (
      <div
        role="alert"
        className="w-full bg-[var(--sev-critical-bg)] border-b border-[var(--sev-critical)] text-[var(--sev-critical)] px-4 py-1.5 text-xs font-medium flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <span className="animate-pulse">⚠️</span>
          <span>
            <strong>Backend Unreachable:</strong> Showing cached intelligence state
            {dataUpdatedAt ? ` from ${formatTime(new Date(dataUpdatedAt).toISOString(), tzMode)}` : ''}.
            Automatic reconnection attempts in progress...
          </span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-dim)]">
          Degraded Operation
        </span>
      </div>
    );
  }

  if (resyncBannerCount && resyncBannerCount > 0) {
    return (
      <div
        role="status"
        className="w-full bg-[var(--ok-bg)] border-b border-[var(--ok)] text-[var(--ok)] px-4 py-1.5 text-xs font-medium flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <span>🔄</span>
          <span>
            <strong>Connection restored:</strong> {resyncBannerCount} alert
            {resyncBannerCount > 1 ? 's' : ''} arrived while you were offline.
          </span>
        </div>
        <button
          type="button"
          onClick={clearResyncBanner}
          className="px-2 py-0.5 rounded text-[11px] font-semibold bg-[var(--ok)] text-black hover:opacity-80 transition-opacity"
        >
          Dismiss
        </button>
      </div>
    );
  }

  return null;
}
