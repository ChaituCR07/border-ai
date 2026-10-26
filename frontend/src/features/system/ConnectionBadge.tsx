import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';

export function ConnectionBadge() {
  const { data, isError, isFetching } = useQuery({
    queryKey: keys.ready,
    queryFn: () => unwrap(api.GET('/api/ready')),
    refetchInterval: POLL_INTERVALS.HEALTH,
    retry: 2,
    staleTime: 5000,
  });

  const isConnected = !isError && data?.status === 'ready';

  return (
    <div
      role="status"
      aria-label={`System Status: ${isConnected ? 'Connected' : isError ? 'Offline' : 'Connecting'}`}
      className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border"
      style={{
        backgroundColor: isConnected
          ? 'var(--ok-bg)'
          : isError
          ? 'var(--sev-critical-bg)'
          : 'var(--warn-bg)',
        borderColor: isConnected
          ? 'var(--ok)'
          : isError
          ? 'var(--sev-critical)'
          : 'var(--warn)',
        color: isConnected
          ? 'var(--ok)'
          : isError
          ? 'var(--sev-critical)'
          : 'var(--warn)',
      }}
    >
      <span
        className={`w-2 h-2 rounded-full ${
          isConnected ? 'bg-[var(--ok)]' : isError ? 'bg-[var(--sev-critical)]' : 'bg-[var(--warn)]'
        } ${isFetching ? 'animate-ping' : ''}`}
      />
      <span>{isConnected ? 'API LIVE' : isError ? 'API OFFLINE' : 'CHECKING'}</span>
    </div>
  );
}
