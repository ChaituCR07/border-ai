import React from 'react';
import type { AlertDetailData } from './useAlertDeepLink';

interface DeepLinkBannerProps {
  alertId: string | null;
  alert: AlertDetailData | null;
  loading: boolean;
  error: string | null;
  onDismiss: () => void;
  onOpenSnapshot?: () => void;
}

export const DeepLinkBanner: React.FC<DeepLinkBannerProps> = ({
  alertId,
  alert,
  loading,
  error,
  onDismiss,
  onOpenSnapshot,
}) => {
  if (!alertId) return null;

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center justify-between px-4 py-2 bg-blue-900/40 border-b border-blue-700/60 text-blue-200 text-xs animate-pulse"
      >
        <div className="flex items-center gap-2">
          <span>🔍</span>
          <span>Loading deep-linked alert <code className="font-mono">{alertId}</code>...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="flex items-center justify-between px-4 py-2 bg-amber-950/70 border-b border-amber-600/70 text-amber-200 text-xs"
      >
        <div className="flex items-center gap-2">
          <span className="text-amber-400 font-bold">⚠️</span>
          <span>{error}</span>
          <span className="font-mono text-amber-300 text-[11px]">({alertId})</span>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="px-2 py-0.5 rounded bg-amber-900/60 hover:bg-amber-800 text-amber-100 text-[11px] font-semibold cursor-pointer"
        >
          Dismiss
        </button>
      </div>
    );
  }

  if (alert) {
    const isResolved = alert.status === 'RESOLVED';
    const isAcked = alert.status === 'ACKNOWLEDGED';

    const bgClass = isResolved
      ? 'bg-emerald-950/70 border-emerald-600/70 text-emerald-200'
      : isAcked
      ? 'bg-cyan-950/70 border-cyan-600/70 text-cyan-200'
      : 'bg-rose-950/70 border-rose-600/70 text-rose-200';

    const icon = isResolved ? '✓' : isAcked ? 'ℹ️' : '🚨';

    return (
      <div
        role="status"
        className={`flex items-center justify-between px-4 py-2 border-b text-xs ${bgClass}`}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold">{icon}</span>
          <span className="font-semibold">
            {isResolved && (
              <>
                Alert <span className="font-mono">{alert.alert_id.slice(0, 8)}</span> resolved
                {alert.resolution ? ` (${alert.resolution})` : ''} by {alert.resolved_by || 'operator'}
              </>
            )}
            {isAcked && (
              <>
                Alert <span className="font-mono">{alert.alert_id.slice(0, 8)}</span> acknowledged by {alert.acknowledged_by || 'operator'}
              </>
            )}
            {!isResolved && !isAcked && (
              <>
                Active Alert <span className="font-mono">{alert.alert_id.slice(0, 8)}</span> ({alert.priority}) on camera {alert.event?.camera_id}
              </>
            )}
          </span>
          {alert.notifications && alert.notifications.total > 0 && (
            <span className="text-[11px] opacity-80 font-mono">
              [Notified: {alert.notifications.sent}/{alert.notifications.total}]
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onOpenSnapshot && (
            <button
              type="button"
              onClick={onOpenSnapshot}
              className="px-2 py-0.5 rounded bg-black/40 hover:bg-black/60 text-white text-[11px] font-semibold cursor-pointer border border-white/20"
            >
              View Evidence
            </button>
          )}
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss deep link banner"
            className="px-2 py-0.5 rounded bg-black/30 hover:bg-black/50 text-[11px] font-semibold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  return null;
};
