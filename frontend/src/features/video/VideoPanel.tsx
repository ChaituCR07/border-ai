import { useMemo } from 'react';
import { MjpegPlayer } from './MjpegPlayer';
import { useCameras, useCameraActivity } from '../cameras/useCameras';
import { useUIStore } from '../../state/uiStore';
import { useOpenAlerts } from '../alerts/useOpenAlerts';
import { getSeverityMeta } from '../../lib/severity';
import { relativeTime } from '../../lib/time';

export function VideoPanel() {
  const { data: cameras } = useCameras();
  const { data: activity } = useCameraActivity();
  const { alerts } = useOpenAlerts();

  const selectedCameraId = useUIStore((s) => s.selectedCameraId);

  const selectedCamera = useMemo(() => {
    if (!cameras) return null;
    return cameras.find((c) => c.camera_id === selectedCameraId) || cameras[0] || null;
  }, [cameras, selectedCameraId]);

  const cameraActivity = useMemo(() => {
    if (!activity || !selectedCamera) return null;
    return activity.find((a) => a.camera_id === selectedCamera.camera_id) || null;
  }, [activity, selectedCamera]);

  const latestAlert = useMemo(() => {
    if (!alerts || !selectedCamera) return null;
    return alerts.find((a) => a.event.camera_id === selectedCamera.camera_id) || null;
  }, [alerts, selectedCamera]);

  if (!selectedCamera) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[var(--bg-panel)] rounded-[var(--radius)] border border-[var(--border)] p-8 text-center">
        <span className="text-4xl mb-2">📹</span>
        <h3 className="text-sm font-semibold text-[var(--text)]">No Camera Selected</h3>
        <p className="text-xs text-[var(--text-dim)] mt-1">
          Select an active camera from the sidebar to inspect live stream.
        </p>
      </div>
    );
  }

  const hasCrit = latestAlert?.priority === 'CRITICAL';
  const alertMeta = latestAlert ? getSeverityMeta(latestAlert.priority) : null;

  return (
    <div className="flex flex-col h-full gap-2">
      <div className="flex items-center justify-between px-3 py-2 bg-[var(--bg-panel)] rounded-[var(--radius-sm)] border border-[var(--border)]">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold text-[var(--text)]">
            {selectedCamera.camera_id}
          </span>
          <span className="text-xs font-medium text-[var(--text-muted)]">
            {selectedCamera.name}
          </span>
          <span className="text-xs text-[var(--text-dim)] hidden sm:inline">
            · {selectedCamera.location_label}
          </span>
        </div>

        {latestAlert && alertMeta && (
          <div
            className="flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold border"
            style={{
              backgroundColor: alertMeta.bgVar,
              borderColor: alertMeta.cssVar,
              color: alertMeta.cssVar,
            }}
          >
            <span>{alertMeta.icon}</span>
            <span>{latestAlert.event.event_type.replace(/_/g, ' ')}</span>
            <span className="text-[10px] text-[var(--text-dim)] ml-1">
              {relativeTime(latestAlert.created_at)}
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 min-h-[300px]">
        <MjpegPlayer
          src={selectedCamera.live_view_url}
          label={selectedCamera.camera_id}
          subLabel={selectedCamera.name}
          hasCriticalAlert={hasCrit}
          className="w-full h-full"
        />
      </div>
    </div>
  );
}
