import { useQuery } from '@tanstack/react-query';

export interface PublicConfigData {
  thresholds: Array<{ name: string; min: number }>;
  escalation: {
    critical_after_s: number;
  };
  realtime: {
    heartbeat_ms: number;
  };
}

export function usePublicConfig() {
  return useQuery<PublicConfigData>({
    queryKey: ['config', 'public'],
    queryFn: async () => {
      const res = await fetch('/api/config/public', {
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Failed to load public configuration: ${res.status}`);
      }
      const json = await res.json();
      return json.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes cache
    refetchOnWindowFocus: false,
  });
}
