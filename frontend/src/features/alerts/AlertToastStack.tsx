import { useEffect, useRef, useState } from 'react';
import type { Toast } from './toastQueue';
import { visible } from './toastQueue';
import { useAcknowledge } from './useAcknowledge';
import { useUIStore } from '../../state/uiStore';
import { formatTime } from '../../lib/time';
import { formatPlate } from '../../lib/plate';

interface AlertToastStackProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
  onViewAlert?: (toast: Toast) => void;
}

export function AlertToastStack({ toasts, onDismiss, onViewAlert }: AlertToastStackProps) {
  const { shown, hidden } = visible(toasts);
  const acknowledge = useAcknowledge();
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);
  const tzMode = useUIStore((s) => s.tzMode);
  const [ackingIds, setAckingIds] = useState<Set<string>>(new Set());
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const firstToastRef = useRef<HTMLDivElement | null>(null);

  // Keyboard shortcut: Alt+A focuses the topmost active toast
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && (e.key === 'a' || e.key === 'A')) {
        e.preventDefault();
        firstToastRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (toasts.length === 0) return null;

  const handleAcknowledge = async (toast: Toast) => {
    if (!toast.alert.persisted) return; // Wait until persisted in DB
    const id = toast.id;
    if (ackingIds.has(id)) return;

    setAckingIds((prev) => new Set(prev).add(id));
    try {
      await acknowledge.mutateAsync(id);
      onDismiss(id);
    } catch {
      // Handled by react-query rollback
    } finally {
      setAckingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleView = (toast: Toast) => {
    setSelectedCamera(toast.alert.event.camera_id);
    if (onViewAlert) {
      onViewAlert(toast);
    }
  };

  return (
    <aside
      aria-label="Live Alert Notifications"
      aria-live="polite"
      className="fixed top-4 right-4 z-50 flex flex-col gap-3 w-96 max-w-[calc(100vw-2rem)] pointer-events-none"
    >
      {shown.map((toast, index) => {
        const isCritical = toast.alert.priority === 'CRITICAL';
        const isAcking = ackingIds.has(toast.id);
        const isPersisted = toast.alert.persisted;

        return (
          <div
            key={toast.id}
            ref={index === 0 ? firstToastRef : undefined}
            tabIndex={0}
            role={isCritical ? 'alert' : 'status'}
            aria-atomic="true"
            onMouseEnter={() => setHoveredId(toast.id)}
            onMouseLeave={() => setHoveredId(null)}
            className={`pointer-events-auto relative p-4 rounded-[var(--radius)] shadow-xl transition-all duration-200 outline-none focus:ring-2 focus:ring-[var(--focus)] ${
              isCritical
                ? 'bg-[var(--bg-panel)] border-2 border-[var(--sev-critical)] shadow-[0_0_20px_rgba(239,68,68,0.25)]'
                : 'bg-[var(--bg-panel)] border-2 border-[var(--sev-high)] shadow-[0_0_15px_rgba(249,115,22,0.2)]'
            }`}
          >
            {/* Header: Priority and Coalesced Badge */}
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <span className="text-lg" aria-hidden="true">
                  {isCritical ? '🚨' : '⚠️'}
                </span>
                <span
                  className={`font-mono text-xs font-bold tracking-wider uppercase ${
                    isCritical ? 'text-[var(--sev-critical)]' : 'text-[var(--sev-high)]'
                  }`}
                >
                  {isCritical ? 'CRITICAL ALERT' : 'HIGH ALERT'}
                </span>
                {toast.count > 1 && (
                  <span
                    title={`${toast.count} coalesced alerts within 20s`}
                    className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-[var(--badge-bg)] text-[var(--text-primary)] border border-[var(--border)]"
                  >
                    ×{toast.count}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => onDismiss(toast.id)}
                aria-label={`Dismiss alert ${toast.id}`}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 rounded transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Body */}
            <div className="mt-2.5 space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-sm text-[var(--text-primary)]">
                  {toast.alert.event.camera_id}
                </span>
                <span className="font-mono text-[11px] text-[var(--text-muted)]">
                  {formatTime(toast.alert.event.timestamp, tzMode)}
                </span>
              </div>

              {toast.alert.event.plate && (
                <div className="flex items-center gap-2">
                  <span className="text-[var(--text-muted)]">Vehicle:</span>
                  <span className="font-mono font-bold text-[var(--accent)]">
                    {formatPlate(toast.alert.event.plate)}
                  </span>
                </div>
              )}

              <div className="flex items-center gap-2">
                <span className="text-[var(--text-muted)]">Event:</span>
                <span className="font-semibold text-[var(--text-primary)]">
                  {toast.alert.event.event_type.replace(/_/g, ' ')}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-[var(--text-muted)]">Threat Score:</span>
                  <span
                    className={`font-mono font-bold ${
                      isCritical ? 'text-[var(--sev-critical)]' : 'text-[var(--sev-high)]'
                    }`}
                  >
                    {toast.alert.event.threat_score}
                  </span>
                </div>
                {!isPersisted && (
                  <span className="text-[10px] text-[var(--warning)] italic">
                    Syncing with DB...
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="mt-3.5 pt-2.5 border-t border-[var(--border)] flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => handleView(toast)}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-[var(--bg-canvas)] hover:bg-[var(--border)] text-[var(--text-primary)] border border-[var(--border)] transition-colors"
              >
                VIEW
              </button>
              <button
                type="button"
                disabled={!isPersisted || isAcking}
                onClick={() => handleAcknowledge(toast)}
                className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
                  !isPersisted
                    ? 'opacity-50 cursor-not-allowed bg-[var(--border)] text-[var(--text-muted)]'
                    : isCritical
                    ? 'bg-[var(--sev-critical)] hover:opacity-90 text-white font-bold'
                    : 'bg-[var(--accent)] hover:opacity-90 text-white'
                }`}
              >
                {isAcking ? 'ACKING...' : 'ACKNOWLEDGE'}
              </button>
            </div>
          </div>
        );
      })}

      {hidden > 0 && (
        <div className="pointer-events-auto text-right">
          <span className="inline-block px-3 py-1 text-xs font-semibold rounded-full bg-[var(--bg-panel)] border border-[var(--border)] text-[var(--text-muted)] shadow">
            +{hidden} more alerts
          </span>
        </div>
      )}
    </aside>
  );
}
