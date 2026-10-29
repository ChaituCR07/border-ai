import React, { useRef, useEffect, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { PlateMatchBadge } from './PlateMatchBadge.js';
import type { Severity, PlateMatch } from './searchSchema.js';

export interface EventItem {
  event_id: string;
  camera_id: string;
  event_type: string;
  track_id: string | null;
  severity: Severity;
  threat_score: number;
  timestamp: string;
  snapshot_url: string | null;
  has_snapshot: boolean;
  snapshot_available: boolean;
  plate?: string | null;
  plate_match?: PlateMatch | null;
  vehicle_id?: string | null;
  person_id?: string | null;
}

interface ResultsTableProps {
  events: EventItem[];
  selectedEventId?: string;
  onSelectEvent: (event: EventItem) => void;
  onInvestigateJourney?: (plate: string) => void;
  hasMore?: boolean;
  loadingMore?: boolean;
  onLoadMore?: () => void;
  className?: string;
}

const SEVERITY_BADGES: Record<Severity, string> = {
  CRITICAL: 'bg-red-950 text-red-300 border-red-800/60',
  HIGH: 'bg-orange-950 text-orange-300 border-orange-800/60',
  MEDIUM: 'bg-yellow-950 text-yellow-300 border-yellow-800/60',
  LOW: 'bg-blue-950 text-blue-300 border-blue-800/60',
};

export const ResultsTable: React.FC<ResultsTableProps> = ({
  events,
  selectedEventId,
  onSelectEvent,
  onInvestigateJourney,
  hasMore = false,
  loadingMore = false,
  onLoadMore,
  className = '',
}) => {
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: events.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 52,
    overscan: 10,
    initialRect: { width: 1000, height: 600 },
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const renderedItems = virtualItems.length > 0
    ? virtualItems
    : events.map((_, index) => ({ index, start: index * 52, size: 52, key: index }));

  // Keyboard navigation: j/k or ArrowDown/ArrowUp
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName;
      if (activeTag === 'INPUT' || activeTag === 'TEXTAREA') return;

      const currentIndex = events.findIndex(ev => ev.event_id === selectedEventId);

      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIndex = Math.min(events.length - 1, currentIndex + 1);
        if (events[nextIndex]) {
          onSelectEvent(events[nextIndex]);
          rowVirtualizer.scrollToIndex(nextIndex);
        }
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex = Math.max(0, currentIndex - 1);
        if (events[prevIndex]) {
          onSelectEvent(events[prevIndex]);
          rowVirtualizer.scrollToIndex(prevIndex);
        }
      }
    },
    [events, selectedEventId, onSelectEvent, rowVirtualizer]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (events.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center p-12 bg-slate-900/50 border border-slate-800 rounded-lg text-center ${className}`}>
        <svg className="w-12 h-12 text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-slate-300 font-medium text-base mb-1">No events match your criteria</p>
        <p className="text-slate-500 text-xs max-w-sm">
          Try widening your time range, clearing active camera filters, or switching plate search mode to lookalike or prefix.
        </p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="grid grid-cols-12 gap-2 px-4 py-2.5 bg-slate-800/80 border-b border-slate-700/80 text-xs font-semibold text-slate-400 uppercase tracking-wider select-none shrink-0">
        <div className="col-span-2">Time</div>
        <div className="col-span-1">Camera</div>
        <div className="col-span-2">Type</div>
        <div className="col-span-1 text-center">Score</div>
        <div className="col-span-1">Severity</div>
        <div className="col-span-3">Subject / Identifier</div>
        <div className="col-span-2 text-right">Actions</div>
      </div>

      {/* Virtualized Rows Container */}
      <div ref={parentRef} className="overflow-y-auto max-h-[640px] divide-y divide-slate-800/60" tabIndex={0} role="region" aria-label="Events list">
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {renderedItems.map((virtualRow) => {
            const ev = events[virtualRow.index]!;
            const isSelected = ev.event_id === selectedEventId;

            return (
              <div
                key={ev.event_id}
                onClick={() => onSelectEvent(ev)}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                className={`grid grid-cols-12 gap-2 items-center px-4 cursor-pointer text-xs transition-colors ${
                  isSelected ? 'bg-sky-950/50 border-l-2 border-sky-500' : 'hover:bg-slate-800/50'
                }`}
              >
                {/* Time */}
                <div className="col-span-2 text-slate-300 font-mono truncate" title={ev.timestamp}>
                  {new Date(ev.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  <span className="text-[10px] text-slate-500 ml-1">
                    {new Date(ev.timestamp).toLocaleDateString([], { month: 'numeric', day: 'numeric' })}
                  </span>
                </div>

                {/* Camera */}
                <div className="col-span-1 text-slate-200 font-mono font-medium truncate">
                  {ev.camera_id}
                </div>

                {/* Type */}
                <div className="col-span-2 text-slate-300 truncate" title={ev.event_type}>
                  {ev.event_type.replace(/_/g, ' ')}
                </div>

                {/* Score */}
                <div className="col-span-1 text-center">
                  <span
                    className={`inline-block px-1.5 py-0.5 rounded text-xs font-mono font-bold ${
                      ev.threat_score >= 80
                        ? 'bg-red-950 text-red-300'
                        : ev.threat_score >= 50
                        ? 'bg-amber-950 text-amber-300'
                        : 'bg-emerald-950 text-emerald-300'
                    }`}
                  >
                    {ev.threat_score}
                  </span>
                </div>

                {/* Severity */}
                <div className="col-span-1">
                  <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium border ${SEVERITY_BADGES[ev.severity]}`}>
                    {ev.severity}
                  </span>
                </div>

                {/* Subject / Identifier */}
                <div className="col-span-3 flex items-center gap-1.5 truncate">
                  {ev.plate ? (
                    <>
                      <span className="font-mono font-semibold text-slate-200 tracking-wide">{ev.plate}</span>
                      <PlateMatchBadge match={ev.plate_match} />
                    </>
                  ) : ev.person_id ? (
                    <span className="font-mono text-purple-300 bg-purple-950/40 px-1 py-0.5 rounded border border-purple-800/40">
                      {ev.person_id}
                    </span>
                  ) : ev.vehicle_id ? (
                    <span className="font-mono text-sky-300 bg-sky-950/40 px-1 py-0.5 rounded border border-sky-800/40">
                      {ev.vehicle_id}
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">None</span>
                  )}
                </div>

                {/* Actions */}
                <div className="col-span-2 flex items-center justify-end gap-1.5">
                  {ev.plate && onInvestigateJourney && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onInvestigateJourney(ev.plate!);
                      }}
                      className="px-2 py-0.5 text-[11px] font-medium rounded bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-800/50"
                      title="Inspect journey for this vehicle plate"
                    >
                      Journey
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectEvent(ev);
                    }}
                    className="px-2 py-0.5 text-[11px] font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                  >
                    Inspect
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Load More Button */}
        {hasMore && (
          <div className="p-3 text-center bg-slate-900 border-t border-slate-800">
            <button
              type="button"
              disabled={loadingMore}
              onClick={onLoadMore}
              className="px-4 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
            >
              {loadingMore ? 'Loading more...' : 'Load more events'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
