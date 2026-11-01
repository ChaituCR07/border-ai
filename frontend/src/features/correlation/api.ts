import { useQuery } from '@tanstack/react-query';
import type {
  JourneyResponse,
  TopologyData,
  SequenceSearchResponse,
} from './types.js';

export interface JourneyQueryParams {
  plate?: string;
  vehicleId?: string;
  from?: string;
  to?: string;
  end_at?: string;
  correlate?: boolean;
}

export function useJourney(params: JourneyQueryParams, options: { enabled?: boolean } = {}) {
  const queryParams = new URLSearchParams();
  if (params.plate) queryParams.set('plate', params.plate);
  if (params.vehicleId) queryParams.set('vehicle_id', params.vehicleId);
  if (params.from) queryParams.set('from', params.from);
  if (params.to) queryParams.set('to', params.to);
  if (params.end_at) queryParams.set('end_at', params.end_at);
  if (params.correlate !== undefined) queryParams.set('correlate', String(params.correlate));

  const hasSubject = Boolean(params.plate || params.vehicleId);
  const isEnabled = (options.enabled ?? true) && hasSubject;

  return useQuery({
    queryKey: ['journey', params],
    queryFn: async (): Promise<JourneyResponse> => {
      const res = await fetch(`/api/investigation/journey?${queryParams.toString()}`);
      if (!res.ok) {
        throw new Error(`Journey request failed: ${res.status} ${res.statusText}`);
      }
      return res.json();
    },
    enabled: isEnabled,
    staleTime: 30_000,
  });
}

export function useTopology() {
  return useQuery({
    queryKey: ['topology'],
    queryFn: async (): Promise<TopologyData> => {
      const res = await fetch('/api/topology');
      if (!res.ok) {
        throw new Error(`Topology request failed: ${res.status} ${res.statusText}`);
      }
      return res.json();
    },
    staleTime: 60_000,
  });
}

export interface SequenceQueryParams {
  cams: string;
  from: string;
  to: string;
  max_hop_gap_s?: number;
  limit?: number;
  purpose: string;
}

export function useSequenceSearch(
  params: SequenceQueryParams,
  options: { enabled?: boolean } = {}
) {
  const queryParams = new URLSearchParams({
    cams: params.cams,
    from: params.from,
    to: params.to,
    purpose: params.purpose,
  });
  if (params.max_hop_gap_s) queryParams.set('max_hop_gap_s', String(params.max_hop_gap_s));
  if (params.limit) queryParams.set('limit', String(params.limit));

  const isEnabled =
    (options.enabled ?? true) &&
    Boolean(params.cams && params.from && params.to && params.purpose.length >= 5);

  return useQuery({
    queryKey: ['sequence-search', params],
    queryFn: async (): Promise<SequenceSearchResponse> => {
      const res = await fetch(`/api/correlation/sequence?${queryParams.toString()}`);
      if (!res.ok) {
        const errorJson = await res.json().catch(() => ({}));
        throw new Error(errorJson.message ?? `Sequence search failed with status ${res.status}`);
      }
      return res.json();
    },
    enabled: isEnabled,
  });
}

