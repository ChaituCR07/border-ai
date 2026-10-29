import React, { useMemo, useState } from 'react';
import type { EventItem } from './ResultsTable.js';
import type { Severity } from './searchSchema.js';

interface TimelineViewProps {
  events: EventItem[];
  fromTime?: string;
  toTime?: string;
  selectedEventId?: string;
  onSelectEvent: (event: EventItem) => void;
  onTimeRangeChange?: (from: string, to: string) => void;
  className?: string;
}

const SEVERITY_DOT_COLORS: Record<Severity, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#3b82f6',
};

export const TimelineView: React.FC<TimelineViewProps> = ({
  events,
  fromTime,
  toTime,
  selectedEventId,
  onSelectEvent,
  onTimeRangeChange,
  className = '',
}) => {
  const [hoveredEvent, setHoveredEvent] = useState<EventItem | null>(null);

  const { cameras, minTime, maxTime, clampedEvents } = useMemo(() => {
    if (events.length === 0) {
      return { cameras: [], minTime: 0, maxTime: 0, clampedEvents: [] };
    }

    const tMin = fromTime ? new Date(fromTime).getTime() : Math.min(...events.map(e => new Date(e.timestamp).getTime()));
    const tMax = toTime ? new Date(toTime).getTime() : Math.max(...events.map(e => new Date(e.timestamp).getTime()));
    const span = Math.max(1000, tMax - tMin);

    const cams = Array.from(new Set(events.map(e => e.camera_id))).sort();

    // Limit to 2000 points max for rendering performance
    const points = events.slice(0, 2000);

    return { cameras: cams, minTime: tMin, maxTime: tMax + (span === 0 ? 1000 : 0), clampedEvents: points };
  }, [events, fromTime, toTime]);

  if (events.length === 0 || cameras.length === 0) {
    return (
      <div className={`p-12 text-center bg-slate-900 border border-slate-800 rounded-lg text-slate-500 text-sm ${className}`}>
        No timeline data available for the selected filters.
      </div>
    );
  }

  const laneHeight = 36;
  const headerHeight = 28;
  const totalHeight = headerHeight + cameras.length * laneHeight;
  const timeSpan = maxTime - minTime || 1;

  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 ${className}`}>
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="font-semibold uppercase tracking-wider">Camera Timeline Lanes</span>
        <span>
          Showing {clampedEvents.length} events across {cameras.length} cameras
        </span>
      </div>

      <div className="relative overflow-x-auto select-none bg-slate-950/60 rounded border border-slate-800/80">
        <svg
          className="w-full min-w-[700px]"
          height={totalHeight}
          style={{ display: 'block' }}
        >
          {/* Time axis header markers */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
            const t = minTime + pct * timeSpan;
            const x = `${pct * 80 + 15}%`;
            return (
              <g key={idx}>
                <line x1={x} y1={headerHeight - 4} x2={x} y2={totalHeight} stroke="#334155" strokeDasharray="3 3" />
                <text x={x} y={16} fill="#94a3b8" fontSize="10" textAnchor="middle" fontFamily="monospace">
                  {new Date(t).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}
                </text>
              </g>
            );
          })}

          {/* Camera Lanes */}
          {cameras.map((cam, idx) => {
            const y = headerHeight + idx * laneHeight;
            return (
              <g key={cam}>
                <rect
                  x="0"
                  y={y}
                  width="100%"
                  height={laneHeight}
                  fill={idx % 2 === 0 ? 'rgba(30, 41, 59, 0.2)' : 'transparent'}
                />
                <text x="12" y={y + 22} fill="#cbd5e1" fontSize="11" fontFamily="monospace" fontWeight="600">
                  {cam}
                </text>
                <line x1="0" y1={y + laneHeight} x2="100%" y2={y + laneHeight} stroke="#1e293b" />
              </g>
            );
          })}

          {/* Event Dots */}
          {clampedEvents.map((ev) => {
            const t = new Date(ev.timestamp).getTime();
            const pct = Math.max(0, Math.min(1, (t - minTime) / timeSpan));
            // Reserve 15% left margin for camera labels, 5% right margin
            const cx = 15 + pct * 80;
            const camIdx = cameras.indexOf(ev.camera_id);
            if (camIdx === -1) return null;
            const cy = headerHeight + camIdx * laneHeight + laneHeight / 2;
            const isSelected = ev.event_id === selectedEventId;

            return (
              <circle
                key={ev.event_id}
                cx={`${cx}%`}
                cy={cy}
                r={isSelected ? 6 : 4}
                fill={SEVERITY_DOT_COLORS[ev.severity] || '#38bdf8'}
                stroke={isSelected ? '#ffffff' : '#0f172a'}
                strokeWidth={isSelected ? 2 : 1}
                className="cursor-pointer hover:opacity-80 transition-transform"
                onClick={() => onSelectEvent(ev)}
                onMouseEnter={() => setHoveredEvent(ev)}
                onMouseLeave={() => setHoveredEvent(null)}
              />
            );
          })}
        </svg>

        {/* Tooltip */}
        {hoveredEvent && (
          <div className="absolute top-2 right-2 bg-slate-900/95 border border-slate-700 rounded p-2 text-xs text-slate-200 pointer-events-none shadow-xl space-y-0.5">
            <div className="font-semibold text-sky-400">{hoveredEvent.event_type.replace(/_/g, ' ')}</div>
            <div>Camera: <span className="font-mono">{hoveredEvent.camera_id}</span></div>
            <div>Score: <span className="font-mono font-bold text-amber-300">{hoveredEvent.threat_score}</span></div>
            {hoveredEvent.plate && <div>Plate: <span className="font-mono">{hoveredEvent.plate}</span></div>}
            <div className="text-[10px] text-slate-400 font-mono">{hoveredEvent.timestamp}</div>
          </div>
        )}
      </div>
    </div>
  );
};
