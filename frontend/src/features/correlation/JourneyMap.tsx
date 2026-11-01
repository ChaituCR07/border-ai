import React from 'react';
import type { Trajectory, TopologyData, LinkClass } from './types.js';

export interface JourneyMapProps {
  trajectory?: Trajectory;
  topology?: TopologyData;
  onSelectCamera?: (cameraId: string) => void;
  className?: string;
}

const LINK_COLOR: Record<LinkClass, { stroke: string; dash?: string }> = {
  PLAUSIBLE: { stroke: 'var(--link-ok, #10b981)' },
  FAST: { stroke: 'var(--link-warn, #f59e0b)', dash: '2 1.5' },
  SLOW: { stroke: 'var(--link-warn, #f59e0b)', dash: '2 1.5' },
  IMPOSSIBLE: { stroke: 'var(--link-bad, #ef4444)', dash: '1 1.5' },
  SIMULTANEOUS: { stroke: 'var(--link-bad, #ef4444)', dash: '1 1.5' },
  OVERLAP_OK: { stroke: 'var(--link-ok, #10b981)' },
  REVISIT: { stroke: 'var(--link-ok, #10b981)' },
  UNLINKED: { stroke: 'var(--link-unknown, #6b7280)', dash: '1 1.5' },
};

export const JourneyMap: React.FC<JourneyMapProps> = ({
  trajectory,
  topology,
  onSelectCamera,
  className = '',
}) => {
  const cameras = topology?.cameras ?? [];
  const links = topology?.links ?? [];

  // Map camera coordinates
  const coordMap = new Map<string, { x: number; y: number; name: string }>();
  for (const c of cameras) {
    coordMap.set(c.camera_id, {
      x: c.map_x,
      // Scale map_y into 0..70 viewBox
      y: (c.map_y * 70) / 100,
      name: c.name || c.camera_id,
    });
  }

  // Active trajectory stops and missed cameras
  const activeSightings = trajectory?.sightings ?? [];
  const activeLinks = trajectory?.links ?? [];

  const visitedCamIds = new Set(activeSightings.map((s) => s.camera_id));
  const missedCamIds = new Set<string>();
  for (const l of activeLinks) {
    for (const m of l.missed_cameras) {
      if (!visitedCamIds.has(m)) {
        missedCamIds.add(m);
      }
    }
  }

  const routeSummary = activeSightings.map((s) => s.camera_id).join(' → ');
  const ariaLabel = routeSummary
    ? `Vehicle route map: ${routeSummary}`
    : 'Schematic camera network map';

  return (
    <div
      className={`journey-map-wrapper ${className}`}
      style={{
        background: 'var(--bg-panel-2, #18212c)',
        borderRadius: 'var(--radius, 10px)',
        border: '1px solid var(--border, #243041)',
        padding: '12px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <svg
        viewBox="0 0 100 70"
        role="img"
        aria-label={ariaLabel}
        style={{
          width: '100%',
          height: 'auto',
          maxHeight: '260px',
          display: 'block',
        }}
      >
        <defs>
          <marker
            id="traj-arrow"
            viewBox="0 0 10 10"
            refX="6"
            refY="5"
            markerWidth="4"
            markerHeight="4"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--border-focus, #38bdf8)" />
          </marker>
        </defs>

        {/* 1. Background Topology Links (faint) */}
        {links.map((l, i) => {
          const a = coordMap.get(l.a);
          const b = coordMap.get(l.b);
          if (!a || !b) return null;
          return (
            <line
              key={`topo-link-${i}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="var(--border, #243041)"
              strokeWidth="0.8"
              strokeDasharray="1 1"
            />
          );
        })}

        {/* 2. Trajectory Active Path Edges (thick, styled by class) */}
        {activeLinks.map((l, i) => {
          const a = coordMap.get(l.from_camera);
          const b = coordMap.get(l.to_camera);
          if (!a || !b) return null;

          const style = LINK_COLOR[l.class] ?? LINK_COLOR.UNLINKED;

          return (
            <g key={`traj-edge-${i}`}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={style.stroke}
                strokeWidth="1.8"
                strokeDasharray={style.dash}
                markerEnd="url(#traj-arrow)"
              />
            </g>
          );
        })}

        {/* 3. Camera Nodes */}
        {cameras.map((cam) => {
          const coords = coordMap.get(cam.camera_id);
          if (!coords) return null;

          const stopIndex = activeSightings.findIndex((s) => s.camera_id === cam.camera_id);
          const isVisited = stopIndex !== -1;
          const isMissed = missedCamIds.has(cam.camera_id);

          if (isMissed) {
            return (
              <g
                key={`cam-node-${cam.camera_id}`}
                aria-label={`${cam.camera_id} expected but not seen`}
                style={{ cursor: 'pointer' }}
                onClick={() => onSelectCamera?.(cam.camera_id)}
              >
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r="3.2"
                  fill="none"
                  stroke="var(--warn, #f5a623)"
                  strokeWidth="0.8"
                  strokeDasharray="1 1"
                />
                <text
                  x={coords.x}
                  y={coords.y + 1}
                  textAnchor="middle"
                  fill="var(--warn, #f5a623)"
                  fontSize="2.4"
                  fontWeight="bold"
                >
                  ?
                </text>
                <text
                  x={coords.x}
                  y={coords.y + 6}
                  textAnchor="middle"
                  fill="var(--warn, #f5a623)"
                  fontSize="2.2"
                  opacity={0.9}
                >
                  {cam.camera_id}
                </text>
              </g>
            );
          }

          if (isVisited) {
            return (
              <g
                key={`cam-node-${cam.camera_id}`}
                aria-label={`Stop ${stopIndex + 1}: ${cam.camera_id}`}
                style={{ cursor: 'pointer' }}
                onClick={() => onSelectCamera?.(cam.camera_id)}
              >
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r="3.5"
                  fill="var(--border-focus, #38bdf8)"
                  stroke="#ffffff"
                  strokeWidth="0.8"
                />
                <text
                  x={coords.x}
                  y={coords.y + 1.1}
                  textAnchor="middle"
                  fill="#0b0f14"
                  fontSize="2.5"
                  fontWeight="bold"
                >
                  {stopIndex + 1}
                </text>
                <text
                  x={coords.x}
                  y={coords.y + 6.2}
                  textAnchor="middle"
                  fill="var(--text, #e6edf3)"
                  fontSize="2.3"
                  fontWeight="600"
                >
                  {cam.camera_id}
                </text>
              </g>
            );
          }

          // Unvisited / Muted camera
          return (
            <g
              key={`cam-node-${cam.camera_id}`}
              aria-label={`${cam.camera_id} (not visited)`}
              style={{ cursor: 'pointer', opacity: 0.45 }}
              onClick={() => onSelectCamera?.(cam.camera_id)}
            >
              <circle
                cx={coords.x}
                cy={coords.y}
                r="2.4"
                fill="var(--bg-panel, #121821)"
                stroke="var(--border-muted, #1c2633)"
                strokeWidth="0.7"
              />
              <text
                x={coords.x}
                y={coords.y + 5.2}
                textAnchor="middle"
                fill="var(--text-muted, #93a1b2)"
                fontSize="2.1"
              >
                {cam.camera_id}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

