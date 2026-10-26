import { useEffect } from 'react';
import { Header } from './features/system/Header';
import { StaleBanner } from './features/system/StaleBanner';
import { CameraSidebar } from './features/cameras/CameraSidebar';
import { VideoGrid } from './features/video/VideoGrid';
import { SeverityCounters } from './features/threats/SeverityCounters';
import { AlertFeed } from './features/alerts/AlertFeed';
import { RecentEvents } from './features/events/RecentEvents';
import { ErrorBoundary } from './features/system/ErrorBoundary';
import { useUIStore } from './state/uiStore';
import { useOpenAlerts } from './features/alerts/useOpenAlerts';
import { useCameras } from './features/cameras/useCameras';

export default function App() {
  const toggleVideoLayout = useUIStore((s) => s.toggleVideoLayout);
  const toggleTzMode = useUIStore((s) => s.toggleTzMode);
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);
  const { data: cameras } = useCameras();
  const { counts } = useOpenAlerts();

  // Dynamic document title with critical alerts badge
  useEffect(() => {
    const crit = counts?.CRITICAL ?? 0;
    if (crit > 0) {
      document.title = `(${crit}) Border AI Command Center`;
    } else {
      document.title = 'Border AI Command Center';
    }
  }, [counts?.CRITICAL]);

  // Global hotkeys (1-9 cameras, G layout, U timezone)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger hotkeys if typing inside an input or textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if (e.key === 'g' || e.key === 'G') {
        e.preventDefault();
        toggleVideoLayout();
      } else if (e.key === 'u' || e.key === 'U') {
        e.preventDefault();
        toggleTzMode();
      } else if (/^[1-9]$/.test(e.key) && cameras && cameras.length > 0) {
        const idx = parseInt(e.key, 10) - 1;
        if (idx < cameras.length && cameras[idx]) {
          e.preventDefault();
          setSelectedCamera(cameras[idx]!.camera_id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [cameras, toggleVideoLayout, toggleTzMode, setSelectedCamera]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[var(--bg-app)] text-[var(--text)] select-none">
      <Header />
      <StaleBanner />

      <div className="flex-1 flex overflow-hidden">
        {/* Camera Navigation Sidebar */}
        <ErrorBoundary fallbackTitle="Camera Sidebar Error">
          <CameraSidebar />
        </ErrorBoundary>

        {/* Center Workspace */}
        <main
          aria-label="Intelligence Dashboard Main Workspace"
          className="flex-1 flex flex-col p-3 overflow-hidden gap-3 min-w-0"
        >
          {/* Live Video Panel / Grid */}
          <section aria-label="Live Video Monitoring" className="flex-[3] min-h-[320px] overflow-hidden">
            <ErrorBoundary fallbackTitle="Video Display Error">
              <VideoGrid />
            </ErrorBoundary>
          </section>

          {/* Recent Events Intelligence Activity */}
          <section aria-label="Recent Detections" className="flex-[2] min-h-[160px] overflow-hidden">
            <ErrorBoundary fallbackTitle="Recent Events Feed Error">
              <RecentEvents />
            </ErrorBoundary>
          </section>

          {/* Alert Severity Summary Counters */}
          <footer className="shrink-0">
            <ErrorBoundary fallbackTitle="Severity Counters Error">
              <SeverityCounters />
            </ErrorBoundary>
          </footer>
        </main>

        {/* Right Alert Feed */}
        <ErrorBoundary fallbackTitle="Alert Feed Error">
          <AlertFeed />
        </ErrorBoundary>
      </div>
    </div>
  );
}
