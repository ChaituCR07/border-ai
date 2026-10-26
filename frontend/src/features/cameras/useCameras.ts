import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '../../api/client';
import { keys } from '../../api/keys';
import { POLL_INTERVALS } from '../../api/intervals';
import type { CameraResource, CameraActivity } from '../../api/types';

export type { CameraResource, CameraActivity };

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
    queryFn: () => unwrap(api.GET('/api/analytics/cameras')).then((r) => r.data),
    refetchInterval: POLL_INTERVALS.CAMERA_ACTIVITY,
    staleTime: 5_000,
  });
}
