import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import type { AlertResource } from '../../api/types';

interface MutationContext {
  snapshots: [readonly unknown[], unknown][];
}

export function useAcknowledge() {
  const queryClient = useQueryClient();

  return useMutation<AlertResource, Error, string, MutationContext>({
    mutationFn: (id: string) =>
      unwrap(
        api.PATCH('/api/alerts/{id}/acknowledge', {
          params: { path: { id } },
          body: {},
        })
      ).then((r) => r.data),

    onMutate: async (id: string) => {
      // Cancel any outgoing refetches so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: ['alerts'] });

      // Snapshot previous query data across any active alerts queries
      const queries = queryClient.getQueriesData<AlertResource[]>({ queryKey: ['alerts'] });
      const snapshots: [readonly unknown[], unknown][] = queries.map(([key, data]) => [key, data]);

      // Optimistically remove the acknowledged alert from the open list
      queryClient.setQueriesData<AlertResource[]>(
        { queryKey: ['alerts'] },
        (old) => (old ? old.filter((alert) => alert.alert_id !== id) : old)
      );

      return { snapshots };
    },

    onError: (_err, _id, context) => {
      // Roll back to previous snapshot on network or server error
      if (context?.snapshots) {
        context.snapshots.forEach(([key, prevData]) => {
          queryClient.setQueryData(key, prevData);
        });
      }
    },

    onSettled: () => {
      // Refetch alerts and threat summary to keep server & client in sync
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'threats'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'cameras'] });
    },
  });
}
