import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';
import type { AlertResource } from '../../api/types';
import type { Severity } from '../../lib/severity';
import { compareSeverityDesc } from '../../lib/severity';
import { useUIStore } from '../../state/uiStore';

export type { AlertResource };

export interface LiveAlerts {
  alerts: AlertResource[];
  counts: Record<Severity, number>;
  transport: 'polling' | 'websocket';
  isStale: boolean;
  lastUpdated: number | null;
}

export function useOpenAlerts(): LiveAlerts {
  const severityFilter = useUIStore((s) => s.severityFilter);
  const selectedCameraId = useUIStore((s) => s.selectedCameraId);
  const selectedCameraOnly = useUIStore((s) => s.selectedCameraOnly);

  const activeCameraFilter = selectedCameraOnly ? selectedCameraId : null;

  const query = useQuery({
    queryKey: keys.openAlerts(severityFilter, activeCameraFilter),
    queryFn: () =>
      unwrap(
        api.GET('/api/alerts', {
          params: {
            query: {
              status: 'OPEN',
              priority: severityFilter ?? undefined,
              camera_id: activeCameraFilter ?? undefined,
              limit: 50,
            },
          },
        })
      ).then((r) => r.data),
    refetchInterval: POLL_INTERVALS.OPEN_ALERTS,
    staleTime: 3000,
  });

  const alerts = useMemo(() => {
    if (!query.data) return [];
    // Sort client side: severity rank desc, then created_at desc (ADR 0019)
    return [...query.data].sort((a, b) => {
      const sevDiff = compareSeverityDesc(a.priority as Severity, b.priority as Severity);
      if (sevDiff !== 0) return sevDiff;
      return b.created_at.localeCompare(a.created_at);
    });
  }, [query.data]);

  const counts = useMemo(() => {
    const res: Record<Severity, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    query.data?.forEach((a) => {
      if (a.priority in res) {
        res[a.priority as Severity]++;
      }
    });
    return res;
  }, [query.data]);

  return {
    alerts,
    counts,
    transport: 'polling',
    isStale: query.isStale || query.isError,
    lastUpdated: query.dataUpdatedAt || null,
  };
}
