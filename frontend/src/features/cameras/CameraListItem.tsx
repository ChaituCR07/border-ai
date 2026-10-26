import React from 'react';
import type { CameraResource, CameraActivity } from './useCameras';
import { relativeTime } from '../../lib/time';

interface Props {
  camera: CameraResource;
  activity?: CameraActivity;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export function CameraListItem({ camera, activity, isSelected, onSelect }: Props) {
  const hasOpenAlerts = (activity?.alerts_open ?? 0) > 0;
  const isEnabled = camera.enabled;

  const dotColor = !isEnabled
    ? 'bg-[var(--offline)]'
    : hasOpenAlerts
    ? 'bg-[var(--sev-critical)]'
    : isSelected
    ? 'bg-[var(--ok)]'
    : 'bg-[var(--sev-low)]';

  const lastEventStr = activity?.last_event_at
    ? `last event ${relativeTime(activity.last_event_at)}`
    : 'no recent events';

  return (
    <div
      role="option"
      aria-selected={isSelected}
      tabIndex={0}
      onClick={() => onSelect(camera.camera_id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(camera.camera_id);
        }
      }}
      className={`p-3 rounded-[var(--radius-sm)] border cursor-pointer transition-all select-none ${
        isSelected
          ? 'bg-[var(--bg-panel-2)] border-[var(--border-focus)] shadow-sm'
          : 'bg-transparent border-transparent hover:bg-[var(--bg-panel-hover)] hover:border-[var(--border)]'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`relative flex h-2.5 w-2.5 shrink-0 rounded-full ${dotColor} ${
              hasOpenAlerts ? 'ring-4 ring-[rgba(255,77,79,0.3)] animate-pulse-slow' : ''
            }`}
          />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-xs font-bold text-[var(--text)]">
                {camera.camera_id}
              </span>
              <span className="text-xs text-[var(--text-muted)] truncate font-medium">
                {camera.name || 'Unnamed Camera'}
              </span>
            </div>
            <div className="text-[11px] text-[var(--text-dim)] truncate mt-0.5">
              {camera.location_label || 'Unassigned Sector'}
            </div>
          </div>
        </div>

        {hasOpenAlerts && (
          <span
            title={`${activity?.alerts_open} active open alert(s)`}
            className="shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[var(--sev-critical-bg)] text-[var(--sev-critical)] border border-[var(--sev-critical)]"
          >
            <span>▲</span>
            <span>{activity?.alerts_open}</span>
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-[10px] text-[var(--text-dim)] mt-2 pt-1.5 border-t border-[var(--border-muted)]">
        <span>{isEnabled ? lastEventStr : 'DISABLED'}</span>
        {activity?.events !== undefined && (
          <span className="font-mono">{activity.events} events</span>
        )}
      </div>
    </div>
  );
}
