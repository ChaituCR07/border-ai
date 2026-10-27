import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { api, unwrap } from '../../api/client';
import { POLL_INTERVALS } from '../../api/intervals';
import type { AlertResource } from '../../api/types';
import type { Severity } from '../../lib/severity';
import { compareSeverityDesc } from '../../lib/severity';
import { useUIStore } from '../../state/uiStore';
import { useLiveAlertsContext, type TransportType } from './LiveAlertsProvider';

export type { AlertResource };

export interface LiveAlerts {
  alerts: AlertResource[];
  counts: Record<Severity, number>;
  transport: TransportType;
  isStale: boolean;
  lastUpdated: number | null;
}

export function useOpenAlerts(): LiveAlerts {
  const severityFilter = useUIStore((s) => s.severityFilter);
  const selectedCameraId = useUIStore((s) => s.selectedCameraId);
  const selectedCameraOnly = useUIStore((s) => s.selectedCameraOnly);

  // Read transport state from LiveAlertsContext
  let transport: TransportType = 'polling';
  try {
    const liveContext = useLiveAlertsContext();
    transport = liveContext.transport;
  } catch {
    // Graceful fallback for standalone component testing without provider
    transport = 'polling';
  }

  // Single shared query key for all open alerts (Task 0 / Task 7)
  const query = useQuery({
    queryKey: ['alerts', 'open', 'all'],
    queryFn: () =>
      unwrap(
        api.GET('/api/alerts', {
          params: {
            query: {
              status: 'OPEN',
              limit: 100,
            },
          },
        })
      ).then((r) => r.data),
    // Polling is active only as fallback when websocket is not open (Task 7)
    refetchInterval: transport === 'websocket' ? false : POLL_INTERVALS.OPEN_ALERTS,
    staleTime: 3000,
  });

  const activeCameraFilter = selectedCameraOnly ? selectedCameraId : null;

  // Filter and sort open alerts client-side
  const alerts = useMemo(() => {
    if (!query.data) return [];

    let filtered = query.data;

    if (severityFilter) {
      filtered = filtered.filter((a) => a.priority === severityFilter);
    }
    if (activeCameraFilter) {
      filtered = filtered.filter((a) => a.event.camera_id === activeCameraFilter);
    }

    // Sort client side: severity rank desc, then created_at desc (ADR 0019)
    return [...filtered].sort((a, b) => {
      const sevDiff = compareSeverityDesc(a.priority as Severity, b.priority as Severity);
      if (sevDiff !== 0) return sevDiff;
      return b.created_at.localeCompare(a.created_at);
    });
  }, [query.data, severityFilter, activeCameraFilter]);

  // Aggregate severity counts from the unfiltered open alerts list
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
    transport,
    isStale: query.isStale || query.isError,
    lastUpdated: query.dataUpdatedAt || null,
  };
}
