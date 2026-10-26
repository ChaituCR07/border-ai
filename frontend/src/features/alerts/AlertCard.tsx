import { useState } from 'react';
import type { AlertResource } from '../../api/types';
import { getSeverityMeta } from '../../lib/severity';
import { formatTime, relativeTime } from '../../lib/time';
import { formatPlate } from '../../lib/plate';
import { useUIStore } from '../../state/uiStore';
import { useAcknowledge } from './useAcknowledge';

interface AlertCardProps {
  alert: AlertResource;
  onViewSnapshot?: (alert: AlertResource) => void;
}

export function AlertCard({ alert, onViewSnapshot }: AlertCardProps) {
  const meta = getSeverityMeta(alert.priority);
  const tzMode = useUIStore((s) => s.tzMode);
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);
  const acknowledge = useAcknowledge();
  const [isAcking, setIsAcking] = useState(false);

  const handleAcknowledge = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isAcking || acknowledge.isPending) return;
    setIsAcking(true);
    try {
      await acknowledge.mutateAsync(alert.alert_id);
    } catch {
      // Error handled by mutation rollback and toast/state
    } finally {
      setIsAcking(false);
    }
  };

  const handleView = () => {
    setSelectedCamera(alert.event.camera_id);
    if (onViewSnapshot) {
      onViewSnapshot(alert);
    }
  };

  const isCritical = alert.priority === 'CRITICAL';

  return (
    <article
      aria-labelledby={`alert-title-${alert.alert_id}`}
      className={`relative p-3 rounded-[var(--radius)] bg-[var(--bg-panel)] border transition-all text-left ${
        isCritical
          ? 'border-[var(--sev-critical)] shadow-sm'
          : 'border-[var(--border)] hover:border-[var(--border-focus)]'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold border"
            style={{
              backgroundColor: meta.bgVar,
              borderColor: meta.cssVar,
              color: meta.cssVar,
            }}
          >
            <span aria-hidden="true">{meta.icon}</span>
            <span>{meta.label}</span>
          </span>

          <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-[var(--bg-panel-2)] text-[var(--text)] border border-[var(--border-muted)]">
            Score {alert.event.threat_score}
          </span>
        </div>

        <div className="text-[11px] text-[var(--text-dim)] font-mono text-right">
          <div>{formatTime(alert.created_at, tzMode)}</div>
          <div>{relativeTime(alert.created_at)}</div>
        </div>
      </div>

      <div className="mb-2.5">
        <div id={`alert-title-${alert.alert_id}`} className="text-xs font-semibold text-[var(--text)]">
          <span className="text-[var(--text-muted)] font-mono mr-1.5">{alert.event.camera_id}</span>
          <span>{alert.event.event_type.replace(/_/g, ' ')}</span>
        </div>

        {alert.event.plate && (
          <div className="mt-1 flex items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-wider text-[var(--text-dim)]">Plate:</span>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-[var(--bg-app)] border border-[var(--border)] text-[var(--text)]">
              {formatPlate(alert.event.plate)}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border-muted)]">
        <button
          type="button"
          onClick={handleView}
          className="px-2.5 py-1 text-xs font-medium rounded bg-[var(--bg-panel-2)] hover:bg-[var(--border)] text-[var(--text)] border border-[var(--border)] transition-colors cursor-pointer"
        >
          View Camera
        </button>

        <button
          type="button"
          onClick={handleAcknowledge}
          disabled={isAcking || acknowledge.isPending}
          className="px-2.5 py-1 text-xs font-semibold rounded bg-[var(--ok)] text-black hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer shadow-sm"
        >
          {isAcking ? 'Acking...' : 'Acknowledge'}
        </button>
      </div>
    </article>
  );
}
