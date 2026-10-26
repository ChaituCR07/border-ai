import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';
import type { components } from '../../api/schema';

export type CameraResource = components['schemas']['CameraResourceSchema'];
export type CameraActivity = {
  camera_id: string;
  events: number;
  alerts_open: number;
  max_threat_score: number;
  last_event_at: string | null;
};

export function useCameras() {
  return useQuery({
    queryKey: keys.cameras,
    queryFn: () => unwrap(api.GET('/api/cameras')).then((r) => r.data),
    refetchInterval: POLL_INTERVALS.CAMERAS,
    staleTime: 15_000,
  });
}

export function useCameraActivity() {
  return useQuery({
    queryKey: keys.cameraActivity,
    queryFn: () => unwrap(api.GET('/api/analytics/cameras')).then((r) => r.data as CameraActivity[]),
    refetchInterval: POLL_INTERVALS.CAMERA_ACTIVITY,
    staleTime: 5_000,
  });
}
