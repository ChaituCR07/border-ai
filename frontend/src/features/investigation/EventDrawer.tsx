import React, { useEffect, useState, useRef } from 'react';
import { PlateMatchBadge } from './PlateMatchBadge.js';
import type { Severity, PlateMatch } from './searchSchema.js';

interface ContextEvent {
  event_id: string;
  camera_id: string;
  event_type: string;
  threat_score: number;
  severity: Severity;
  timestamp: string;
  plate?: string | null;
  plate_match?: PlateMatch | null;
  snapshot_url?: string | null;
  snapshot_available?: boolean;
}

interface EventContextResponse {
  data: {
    event: ContextEvent & {
      metadata?: Record<string, unknown>;
      explanation?: { factors?: { name: string; points: number }[] } | null;
    };
    same_camera_around: ContextEvent[];
    same_subject_elsewhere: ContextEvent[];
    alert?: { alert_id: string; status: string; priority: string } | null;
  };
}

interface EventDrawerProps {
  eventId: string | null;
  onClose: () => void;
  onSelectEventId?: (id: string) => void;
  onFilterCamera?: (cam: string) => void;
  onFilterPlate?: (plate: string) => void;
  onViewJourney?: (plate: string) => void;
  className?: string;
}

export const EventDrawer: React.FC<EventDrawerProps> = ({
  eventId,
  onClose,
  onSelectEventId,
  onFilterCamera,
  onFilterPlate,
  onViewJourney,
  className = '',
}) => {
  const [data, setData] = useState<EventContextResponse['data'] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Fetch context data when eventId changes
  useEffect(() => {
    if (!eventId) {
      setData(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    fetch(`/api/events/${eventId}/context?window_s=60`)
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error?.message || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((json: EventContextResponse) => {
        if (active) {
          setData(json.data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [eventId]);

  if (!eventId) return null;

  const event = data?.event;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Event Detail Drawer"
      ref={drawerRef}
      className={`fixed inset-y-0 right-0 z-40 w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col overflow-hidden text-slate-100 ${className}`}
    >
      {/* Drawer Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-950/80 shrink-0">
        <div>
          <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
            Event Investigation
          </h2>
          <span className="text-xs text-slate-400 font-mono">{eventId}</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close drawer"
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Drawer Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {loading && (
          <div className="flex items-center justify-center p-12 text-slate-400 text-sm">
            <div className="w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mr-3" />
            Loading event context...
          </div>
        )}

        {error && (
          <div className="p-4 rounded-lg bg-red-950/40 border border-red-800/60 text-red-200 text-xs">
            <div className="font-semibold mb-1">Failed to load event details</div>
            <div>{error}</div>
          </div>
        )}

        {event && (
          <>
            {/* Snapshot with fallback */}
            <div className="relative rounded-lg overflow-hidden bg-slate-950 border border-slate-800 aspect-video flex items-center justify-center">
              {event.snapshot_available && event.snapshot_url ? (
                <img
                  src={event.snapshot_url}
                  alt={`Snapshot from camera ${event.camera_id}`}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center justify-center p-6 text-slate-500 text-center">
                  <svg className="w-10 h-10 mb-2 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span className="text-xs font-medium">Snapshot no longer available</span>
                  <span className="text-[10px] text-slate-600 mt-0.5">Expired per 48h retention policy</span>
                </div>
              )}
            </div>

            {/* Score & Attributes */}
            <div className="grid grid-cols-2 gap-3 p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Threat Score</span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-sm font-bold font-mono ${
                    event.threat_score >= 80
                      ? 'bg-red-950 text-red-300'
                      : event.threat_score >= 50
                      ? 'bg-amber-950 text-amber-300'
                      : 'bg-emerald-950 text-emerald-300'
                  }`}
                >
                  {event.threat_score} / 100
                </span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5">Severity</span>
                <span className="inline-block px-2 py-0.5 rounded font-semibold text-xs border bg-slate-900 border-slate-700">
                  {event.severity}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5">Camera</span>
                <span className="font-mono text-slate-200 font-medium">{event.camera_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5">Time</span>
                <span className="font-mono text-slate-300 text-[11px]">{event.timestamp}</span>
              </div>
            </div>

            {/* Deep Links / Actions */}
            <div className="flex flex-wrap gap-2">
              {onFilterCamera && (
                <button
                  type="button"
                  onClick={() => onFilterCamera(event.camera_id)}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                >
                  Filter this camera ({event.camera_id})
                </button>
              )}
              {event.plate && onFilterPlate && (
                <button
                  type="button"
                  onClick={() => onFilterPlate(event.plate!)}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-sky-950 hover:bg-sky-900 text-sky-200 border border-sky-800/60 transition-colors"
                >
                  Filter this plate ({event.plate})
                </button>
              )}
              {event.plate && onViewJourney && (
                <button
                  type="button"
                  onClick={() => onViewJourney(event.plate!)}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-indigo-950 hover:bg-indigo-900 text-indigo-200 border border-indigo-800/60 transition-colors"
                >
                  View Vehicle Journey
                </button>
              )}
            </div>

            {/* Explanation Breakdown */}
            {event.explanation?.factors && event.explanation.factors.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Threat Explanation Factors
                </h3>
                <div className="space-y-1.5 p-3 rounded-lg bg-slate-950/40 border border-slate-800">
                  {event.explanation.factors.map((f, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-mono capitalize">{f.name.replace(/_/g, ' ')}</span>
                      <span className="font-mono text-amber-400 font-bold">+{f.points} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Context: Same camera around (±60s) */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Same Camera ({event.camera_id}) ±60s ({data?.same_camera_around.length ?? 0})
              </h3>
              {data?.same_camera_around.length === 0 ? (
                <div className="text-xs text-slate-500 italic p-2 bg-slate-950/30 rounded border border-slate-800/40">
                  No other events on this camera within ±60 seconds.
                </div>
              ) : (
                <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
                  {data?.same_camera_around.map((c) => (
                    <div
                      key={c.event_id}
                      onClick={() => onSelectEventId?.(c.event_id)}
                      className="flex items-center justify-between p-2 rounded bg-slate-950/40 hover:bg-slate-800/60 cursor-pointer text-xs border border-slate-800/60"
                    >
                      <div className="truncate mr-2">
                        <span className="font-medium text-slate-200 mr-2">{c.event_type.replace(/_/g, ' ')}</span>
                        {c.plate && <span className="font-mono text-sky-300">{c.plate}</span>}
                      </div>
                      <span className="font-mono text-[10px] text-slate-400 shrink-0">
                        {new Date(c.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Context: Same subject elsewhere (±15m) */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Same Subject Elsewhere ±15m ({data?.same_subject_elsewhere.length ?? 0})
              </h3>
              {data?.same_subject_elsewhere.length === 0 ? (
                <div className="text-xs text-slate-500 italic p-2 bg-slate-950/30 rounded border border-slate-800/40">
                  No cross-camera sightings for this subject within ±15 minutes.
                </div>
              ) : (
                <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
                  {data?.same_subject_elsewhere.map((c) => (
                    <div
                      key={c.event_id}
                      onClick={() => onSelectEventId?.(c.event_id)}
                      className="flex items-center justify-between p-2 rounded bg-slate-950/40 hover:bg-slate-800/60 cursor-pointer text-xs border border-slate-800/60"
                    >
                      <div className="truncate mr-2">
                        <span className="font-mono text-sky-400 font-semibold mr-2">{c.camera_id}</span>
                        <span className="text-slate-300">{c.event_type.replace(/_/g, ' ')}</span>
                      </div>
                      <span className="font-mono text-[10px] text-slate-400 shrink-0">
                        {new Date(c.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
