import React from 'react';
import type { Trajectory } from './types.js';

export interface TrajectoryTabsProps {
  trajectories: Trajectory[];
  selectedTrajectoryId: string;
  onSelectTrajectory: (id: string) => void;
  className?: string;
}

export const TrajectoryTabs: React.FC<TrajectoryTabsProps> = ({
  trajectories,
  selectedTrajectoryId,
  onSelectTrajectory,
  className = '',
}) => {
  if (trajectories.length < 2) {
    return null;
  }

  return (
    <div
      className={`trajectory-tabs-container ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        margin: '6px 0',
      }}
    >
      {/* Alert banner for multiple trajectories */}
      <div
        role="alert"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: 'var(--sev-high-bg, rgba(255, 159, 26, 0.15))',
          border: '1px solid var(--sev-high, #ff9f1a)',
          borderRadius: 'var(--radius-sm, 6px)',
          fontSize: '0.8rem',
          color: 'var(--text, #e6edf3)',
        }}
      >
        <span style={{ color: 'var(--sev-high, #ff9f1a)', fontWeight: 'bold' }}>⚠</span>
        <span>
          This plate appears on <strong>{trajectories.length} incompatible trajectories</strong> — possible
          duplicated plate or misread. This is a lead, not a conclusion.
        </span>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted, #93a1b2)', fontWeight: 500 }}>
          Trajectory:
        </span>

        {trajectories.map((t) => {
          const isSelected = t.id === selectedTrajectoryId;
          const confPercent = Math.round(t.confidence * 100);

          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onSelectTrajectory(t.id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: isSelected ? 600 : 500,
                background: isSelected ? 'var(--bg-panel-hover, #1f2c3b)' : 'var(--bg-panel-2, #18212c)',
                color: isSelected ? 'var(--border-focus, #38bdf8)' : 'var(--text-muted, #93a1b2)',
                border: isSelected ? '1px solid var(--border-focus, #38bdf8)' : '1px solid var(--border, #243041)',
                cursor: 'pointer',
              }}
            >
              <span>{t.id}</span>
              <span style={{ opacity: 0.8, fontSize: '0.75rem' }}>({confPercent}%)</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

