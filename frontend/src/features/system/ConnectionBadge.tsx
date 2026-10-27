import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';
import { useLiveAlertsContext } from '../alerts/LiveAlertsProvider';

export function ConnectionBadge() {
  const { data, isError } = useQuery({
    queryKey: keys.ready,
    queryFn: () => unwrap(api.GET('/api/ready') as any) as Promise<{ status?: string }>,
    refetchInterval: POLL_INTERVALS.HEALTH,
    retry: 2,
    staleTime: 5000,
  });

  let transport: 'websocket' | 'polling' = 'polling';
  let socketStatus = 'closed';

  try {
    const live = useLiveAlertsContext();
    transport = live.transport;
    socketStatus = live.socketStatus;
  } catch {
    // Context fallback for isolated tests
  }

  const isApiDown = isError || (data && data.status !== 'ready');

  let badgeText = '● LIVE (WS)';
  let bgVar = 'var(--ok-bg)';
  let borderVar = 'var(--ok)';
  let textVar = 'var(--ok)';
  let dotClass = 'bg-[var(--ok)]';

  if (isApiDown) {
    badgeText = '● OFFLINE';
    bgVar = 'var(--sev-critical-bg)';
    borderVar = 'var(--sev-critical)';
    textVar = 'var(--sev-critical)';
    dotClass = 'bg-[var(--sev-critical)]';
  } else if (transport === 'websocket' && socketStatus === 'open') {
    badgeText = '● LIVE';
    bgVar = 'var(--ok-bg)';
    borderVar = 'var(--ok)';
    textVar = 'var(--ok)';
    dotClass = 'bg-[var(--ok)]';
  } else if (socketStatus === 'connecting') {
    badgeText = '◌ RECONNECTING…';
    bgVar = 'var(--warn-bg)';
    borderVar = 'var(--warn)';
    textVar = 'var(--warn)';
    dotClass = 'bg-[var(--warn)] animate-pulse';
  } else {
    // Polling fallback
    badgeText = '● LIVE (polling 5 s)';
    bgVar = 'var(--warn-bg)';
    borderVar = 'var(--warn)';
    textVar = 'var(--warn)';
    dotClass = 'bg-[var(--warn)]';
  }

  return (
    <div
      role="status"
      aria-label={`System Status: ${badgeText.replace(/^[●◌]\s*/, '')}`}
      className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium border transition-colors select-none"
      style={{
        backgroundColor: bgVar,
        borderColor: borderVar,
        color: textVar,
      }}
    >
      <span className={`w-2 h-2 rounded-full ${dotClass}`} />
      <span>{badgeText.replace(/^[●◌]\s*/, '')}</span>
    </div>
  );
}
