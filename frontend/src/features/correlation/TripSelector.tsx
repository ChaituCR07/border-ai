import React from 'react';
import type { Trip } from './types.js';

export interface TripSelectorProps {
  trips: Trip[];
  selectedTripId: string;
  onSelectTrip: (tripId: string) => void;
  className?: string;
}

export const TripSelector: React.FC<TripSelectorProps> = ({
  trips,
  selectedTripId,
  onSelectTrip,
  className = '',
}) => {
  if (trips.length <= 1) {
    return null;
  }

  const selectedIndex = trips.findIndex((t) => t.trip_id === selectedTripId);
  const earlierCount = Math.max(0, trips.length - 1 - (selectedIndex >= 0 ? selectedIndex : 0));

  return (
    <div
      className={`trip-selector ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        fontSize: '0.8rem',
      }}
    >
      <label htmlFor="trip-select" style={{ color: 'var(--text-muted, #93a1b2)', fontWeight: 500 }}>
        Trip:
      </label>

      <select
        id="trip-select"
        value={selectedTripId}
        onChange={(e) => onSelectTrip(e.target.value)}
        style={{
          background: 'var(--bg-panel-2, #18212c)',
          color: 'var(--text, #e6edf3)',
          border: '1px solid var(--border, #243041)',
          borderRadius: 'var(--radius-sm, 6px)',
          padding: '4px 8px',
          fontSize: '0.8rem',
          cursor: 'pointer',
        }}
      >
        {trips.map((t, i) => (
          <option key={t.trip_id} value={t.trip_id}>
            {t.trip_id} {i === trips.length - 1 ? '(latest)' : ''} ({t.trajectories.length} trajs)
          </option>
        ))}
      </select>

      {earlierCount > 0 && (
        <span style={{ color: 'var(--text-dim, #64748b)', fontSize: '0.75rem' }}>
          {earlierCount} earlier {earlierCount === 1 ? 'trip' : 'trips'}
        </span>
      )}
    </div>
  );
};

