import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';
import type { EventItem } from '../../api/types';

export function useRecentEvents(limit: number = 10) {
  return useQuery<EventItem[]>({
    queryKey: keys.recentEvents(limit),
    queryFn: () =>
      unwrap(
        api.GET('/api/events', {
          params: { query: { limit } },
        })
      ).then((r) => r.data),
    refetchInterval: POLL_INTERVALS.RECENT_EVENTS,
    staleTime: 5000,
  });
}
