import { useEffect, useMemo } from 'react';
import { useCameras, useCameraActivity } from './useCameras';
import type { CameraActivity } from '../../api/types';
import { CameraListItem } from './CameraListItem';
import { useUIStore } from '../../state/uiStore';

export function CameraSidebar() {
  const { data: cameras, isLoading, isError } = useCameras();
  const { data: activity } = useCameraActivity();

  const selectedCameraId = useUIStore((s) => s.selectedCameraId);
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);
  const searchQuery = useUIStore((s) => s.cameraSearchQuery);
  const setSearchQuery = useUIStore((s) => s.setCameraSearchQuery);

  const activityMap = useMemo(() => {
    const map = new Map<string, CameraActivity>();
    activity?.forEach((a) => map.set(a.camera_id, a));
    return map;
  }, [activity]);

  // Auto-select first camera once loaded if none selected
  useEffect(() => {
    if (cameras && cameras.length > 0 && !selectedCameraId) {
      const firstEnabled = cameras.find((c) => c.enabled) || cameras[0];
      if (firstEnabled) setSelectedCamera(firstEnabled.camera_id);
    }
  }, [cameras, selectedCameraId, setSelectedCamera]);

  const filteredCameras = useMemo(() => {
    if (!cameras) return [];
    let list = [...cameras];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (c) =>
          c.camera_id.toLowerCase().includes(q) ||
          (c.name && c.name.toLowerCase().includes(q)) ||
          (c.location_label && c.location_label.toLowerCase().includes(q))
      );
    }

    // Sort: alerting cameras first, then enabled, then by ID
    return list.sort((a, b) => {
      const actA = activityMap.get(a.camera_id)?.alerts_open ?? 0;
      const actB = activityMap.get(b.camera_id)?.alerts_open ?? 0;
      if (actA > 0 && actB === 0) return -1;
      if (actB > 0 && actA === 0) return 1;
      if (a.enabled && !b.enabled) return -1;
      if (!a.enabled && b.enabled) return 1;
      return a.camera_id.localeCompare(b.camera_id);
    });
  }, [cameras, searchQuery, activityMap]);

  return (
    <aside
      aria-label="Cameras"
      className="w-72 md:w-80 border-r border-[var(--border)] bg-[var(--bg-panel)] flex flex-col shrink-0 h-full overflow-hidden select-none"
    >
      <div className="p-3 border-b border-[var(--border)]">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
            Camera Inventory
          </h2>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[var(--border-muted)] text-[var(--text-dim)]">
            {filteredCameras.length} / {cameras?.length ?? 0}
          </span>
        </div>

        <div className="relative">
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter camera or sector..."
            aria-label="Filter cameras"
            className="w-full bg-[var(--bg-app)] border border-[var(--border)] rounded px-2.5 py-1.5 text-xs text-[var(--text)] placeholder:text-[var(--text-dim)] focus:border-[var(--border-focus)] focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text)] cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      <div
        role="listbox"
        aria-label="Camera selection list"
        className="flex-1 overflow-y-auto p-2 space-y-1"
      >
        {isLoading && (
          <div className="space-y-2 p-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-16 rounded bg-[var(--bg-panel-2)] animate-pulse border border-[var(--border-muted)]"
              />
            ))}
          </div>
        )}

        {isError && (
          <div className="p-4 text-center text-xs text-[var(--sev-critical)]">
            Failed to load cameras. Retrying...
          </div>
        )}

        {!isLoading && filteredCameras.length === 0 && (
          <div className="p-6 text-center text-xs text-[var(--text-dim)]">
            No matching cameras found.
          </div>
        )}

        {filteredCameras.map((camera) => (
          <CameraListItem
            key={camera.camera_id}
            camera={camera}
            activity={activityMap.get(camera.camera_id)}
            isSelected={camera.camera_id === selectedCameraId}
            onSelect={setSelectedCamera}
          />
        ))}
      </div>
    </aside>
  );
}
