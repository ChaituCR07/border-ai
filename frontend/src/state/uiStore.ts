import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Severity } from '../lib/severity';
import type { TzMode } from '../lib/time';

export type VideoLayout = '1x1' | '2x2';

export interface SnapshotDrawerData {
  alertId?: string;
  eventId?: string;
  title: string;
  cameraName?: string;
  timestamp?: string;
  snapshotUrl?: string | null;
  snapshotAvailable?: boolean;
  threatScore?: number;
  severity?: string;
  explanation?: Record<string, unknown> | null;
}

export interface UIState {
  selectedCameraId: string | null;
  videoLayout: VideoLayout;
  tzMode: TzMode;
  severityFilter: Severity | null;
  selectedCameraOnly: boolean;
  cameraSearchQuery: string;
  activeSnapshotDrawer: SnapshotDrawerData | null;

  // Actions
  setSelectedCamera: (cameraId: string | null) => void;
  setVideoLayout: (layout: VideoLayout) => void;
  toggleVideoLayout: () => void;
  setTzMode: (mode: TzMode) => void;
  toggleTzMode: () => void;
  setSeverityFilter: (severity: Severity | null) => void;
  setSelectedCameraOnly: (value: boolean) => void;
  setCameraSearchQuery: (query: string) => void;
  openSnapshotDrawer: (data: SnapshotDrawerData) => void;
  closeSnapshotDrawer: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      selectedCameraId: null,
      videoLayout: '1x1',
      tzMode: 'UTC',
      severityFilter: null,
      selectedCameraOnly: false,
      cameraSearchQuery: '',
      activeSnapshotDrawer: null,

      setSelectedCamera: (selectedCameraId) => set({ selectedCameraId }),
      setVideoLayout: (videoLayout) => set({ videoLayout }),
      toggleVideoLayout: () =>
        set((s) => ({ videoLayout: s.videoLayout === '1x1' ? '2x2' : '1x1' })),
      setTzMode: (tzMode) => set({ tzMode }),
      toggleTzMode: () => set((s) => ({ tzMode: s.tzMode === 'UTC' ? 'LOCAL' : 'UTC' })),
      setSeverityFilter: (severityFilter) => set({ severityFilter }),
      setSelectedCameraOnly: (selectedCameraOnly) => set({ selectedCameraOnly }),
      setCameraSearchQuery: (cameraSearchQuery) => set({ cameraSearchQuery }),
      openSnapshotDrawer: (activeSnapshotDrawer) => set({ activeSnapshotDrawer }),
      closeSnapshotDrawer: () => set({ activeSnapshotDrawer: null }),
    }),
    {
      name: 'borderai_dashboard_ui_v1',
      partialize: (state) => ({
        videoLayout: state.videoLayout,
        tzMode: state.tzMode,
        selectedCameraOnly: state.selectedCameraOnly,
      }),
    }
  )
);
