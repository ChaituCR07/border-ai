import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';

export function useThreatSummary(windowHours: number = 24) {
  const to = new Date();
  const from = new Date(to.getTime() - windowHours * 3600_000);

  return useQuery({
    queryKey: keys.threats(`${windowHours}h`),
    queryFn: () =>
      unwrap(
        api.GET('/api/analytics/threats', {
          params: { query: { from: from.toISOString(), to: to.toISOString() } },
        })
      ).then((r) => r.data),
    refetchInterval: POLL_INTERVALS.THREATS,
    placeholderData: keepPreviousData,
    staleTime: 4000,
  });
}
