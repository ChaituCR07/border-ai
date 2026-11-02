import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './features/system/Header';
import { StaleBanner } from './features/system/StaleBanner';
import { DeepLinkBanner } from './features/alerts/DeepLinkBanner';
import { useAlertDeepLink } from './features/alerts/useAlertDeepLink';
import { CameraSidebar } from './features/cameras/CameraSidebar';
import { VideoGrid } from './features/video/VideoGrid';
import { SeverityCounters } from './features/threats/SeverityCounters';
import { AlertFeed } from './features/alerts/AlertFeed';
import { RecentEvents } from './features/events/RecentEvents';
import { ErrorBoundary } from './features/system/ErrorBoundary';
import { LiveAlertsProvider } from './features/alerts/LiveAlertsProvider';
import { useUIStore } from './state/uiStore';
import { useOpenAlerts } from './features/alerts/useOpenAlerts';
import { useCameras } from './features/cameras/useCameras';
import { InvestigationPage } from './features/investigation/InvestigationPage';

function AppShell() {
  const toggleVideoLayout = useUIStore((s) => s.toggleVideoLayout);
  const toggleTzMode = useUIStore((s) => s.toggleTzMode);
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);
  const openSnapshotDrawer = useUIStore((s) => s.openSnapshotDrawer);
  const { data: cameras } = useCameras();
  const { counts } = useOpenAlerts();

  const { alertId, alert, loading, error, clearAlertParam } = useAlertDeepLink((loadedAlert) => {
    openSnapshotDrawer({
      alertId: loadedAlert.alert_id,
      eventId: loadedAlert.event_id,
      title: loadedAlert.event?.event_type?.replace(/_/g, ' ') || 'Alert Detail',
      cameraName: loadedAlert.event?.camera_id,
      timestamp: loadedAlert.created_at,
      snapshotUrl: loadedAlert.event?.snapshot_url,
      snapshotAvailable: Boolean(loadedAlert.event?.snapshot_url),
      threatScore: loadedAlert.event?.threat_score,
      severity: loadedAlert.priority,
      explanation: loadedAlert.explanation,
    });
  });

  // Dynamic document title with critical alerts badge
  useEffect(() => {
    const crit = counts?.CRITICAL ?? 0;
    if (crit > 0) {
      document.title = `(${crit}) 🚨 Border AI Command Center`;
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
      <DeepLinkBanner
        alertId={alertId}
        alert={alert}
        loading={loading}
        error={error}
        onDismiss={clearAlertParam}
        onOpenSnapshot={
          alert
            ? () =>
                openSnapshotDrawer({
                  alertId: alert.alert_id,
                  eventId: alert.event_id,
                  title: alert.event?.event_type?.replace(/_/g, ' ') || 'Alert Detail',
                  cameraName: alert.event?.camera_id,
                  timestamp: alert.created_at,
                  snapshotUrl: alert.event?.snapshot_url,
                  snapshotAvailable: Boolean(alert.event?.snapshot_url),
                  threatScore: alert.event?.threat_score,
                  severity: alert.priority,
                  explanation: alert.explanation,
                })
            : undefined
        }
      />

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

export default function App() {
  return (
    <BrowserRouter>
      <LiveAlertsProvider>
        <Routes>
          <Route path="/" element={<AppShell />} />
          <Route path="/investigation" element={<InvestigationPage />} />
        </Routes>
      </LiveAlertsProvider>
    </BrowserRouter>
  );
}
