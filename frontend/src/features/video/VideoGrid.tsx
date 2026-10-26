import { useMemo } from 'react';
import { useUIStore } from '../../state/uiStore';
import { useCameras } from '../cameras/useCameras';
import { useOpenAlerts } from '../alerts/useOpenAlerts';
import { MjpegPlayer } from './MjpegPlayer';
import { VideoPanel } from './VideoPanel';

export function VideoGrid() {
  const videoLayout = useUIStore((s) => s.videoLayout);
  const selectedCameraId = useUIStore((s) => s.selectedCameraId);
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);

  const { data: cameras } = useCameras();
  const { alerts } = useOpenAlerts();

  const gridCameras = useMemo(() => {
    if (!cameras || cameras.length === 0) return [];
    // Max 4 cameras for 2x2 grid (ADR 0018 connection safety)
    const active = cameras.filter((c) => c.enabled);
    if (active.length <= 4) return active;

    const selectedIdx = active.findIndex((c) => c.camera_id === selectedCameraId);
    if (selectedIdx === -1) return active.slice(0, 4);

    // Keep selected camera in top-left, fill next 3
    const result = [active[selectedIdx]!];
    for (let i = 0; i < active.length && result.length < 4; i++) {
      if (i !== selectedIdx) result.push(active[i]!);
    }
    return result;
  }, [cameras, selectedCameraId]);

  if (videoLayout === '1x1') {
    return <VideoPanel />;
  }

  return (
    <div className="grid grid-cols-2 gap-2 h-full">
      {gridCameras.map((camera) => {
        const isSelected = camera.camera_id === selectedCameraId;
        const hasCrit = alerts.some(
          (a) => a.event.camera_id === camera.camera_id && a.priority === 'CRITICAL'
        );

        return (
          <div
            key={camera.camera_id}
            onClick={() => setSelectedCamera(camera.camera_id)}
            className={`cursor-pointer transition-all rounded-[var(--radius)] overflow-hidden ${
              isSelected ? 'ring-2 ring-[var(--border-focus)]' : ''
            }`}
          >
            <MjpegPlayer
              src={camera.live_view_url}
              label={camera.camera_id}
              subLabel={camera.name}
              hasCriticalAlert={hasCrit}
              className="w-full h-full"
            />
          </div>
        );
      })}
    </div>
  );
}
