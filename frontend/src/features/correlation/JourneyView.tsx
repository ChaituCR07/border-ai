import React, { useState, useEffect } from 'react';
import { useJourney, useTopology } from './api.js';
import { JourneyMap } from './JourneyMap.js';
import { TripSelector } from './TripSelector.js';
import { TrajectoryTabs } from './TrajectoryTabs.js';
import { LinkChip } from './LinkChip.js';
import { AnomalyList } from './AnomalyList.js';
import { ConfidenceBadge } from './ConfidenceBadge.js';

export interface JourneyViewProps {
  plate?: string;
  vehicleId?: string;
  from?: string;
  to?: string;
  onClose?: () => void;
  onSelectSighting?: (cameraId: string, from: string, to: string) => void;
  className?: string;
}

export const JourneyView: React.FC<JourneyViewProps> = ({
  plate,
  vehicleId,
  from,
  to,
  onClose,
  onSelectSighting,
  className = '',
}) => {
  const { data: journeyResp, isLoading, isError, error } = useJourney({
    plate,
    vehicleId,
    from,
    to,
    correlate: true,
  });

  const { data: topology } = useTopology();

  const correlation = journeyResp?.data?.correlation;
  const trips = correlation?.trips ?? [];

  const [selectedTripId, setSelectedTripId] = useState<string>('');
  const [selectedTrajectoryId, setSelectedTrajectoryId] = useState<string>('');

  // Default to latest trip
  useEffect(() => {
    if (trips.length > 0 && !selectedTripId) {
      const latestTrip = trips[trips.length - 1]!;
      setSelectedTripId(latestTrip.trip_id);
      if (latestTrip.trajectories.length > 0) {
        setSelectedTrajectoryId(latestTrip.trajectories[0]!.id);
      }
    }
  }, [trips, selectedTripId]);

  const currentTrip = trips.find((t) => t.trip_id === selectedTripId) ?? trips[0];
  const trajectories = currentTrip?.trajectories ?? [];
  const currentTrajectory =
    trajectories.find((t) => t.id === selectedTrajectoryId) ?? trajectories[0];

  const handleTripChange = (tripId: string) => {
    setSelectedTripId(tripId);
    const trip = trips.find((t) => t.trip_id === tripId);
    if (trip && trip.trajectories.length > 0) {
      setSelectedTrajectoryId(trip.trajectories[0]!.id);
    }
  };

  if (isLoading) {
    return (
      <div
        className={`journey-view-loading ${className}`}
        style={{
          padding: '24px',
          textAlign: 'center',
          color: 'var(--text-muted, #93a1b2)',
          background: 'var(--bg-panel, #121821)',
          borderRadius: 'var(--radius, 10px)',
          border: '1px solid var(--border, #243041)',
        }}
      >
        <span style={{ fontSize: '0.9rem' }}>Correlating journey...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className={`journey-view-error ${className}`}
        style={{
          padding: '16px',
          color: 'var(--sev-critical, #ff4d4f)',
          background: 'var(--sev-critical-bg, rgba(255, 77, 79, 0.15))',
          borderRadius: 'var(--radius, 10px)',
          border: '1px solid var(--sev-critical, #ff4d4f)',
        }}
      >
        <span>Error loading journey: {(error as Error)?.message || 'Failed to fetch journey'}</span>
      </div>
    );
  }

  const subject = plate ?? vehicleId ?? 'Unknown Vehicle';
  const warnings = journeyResp?.meta?.warnings ?? [];

  return (
    <div
      className={`journey-view ${className}`}
      style={{
        background: 'var(--bg-panel, #121821)',
        borderRadius: 'var(--radius, 10px)',
        border: '1px solid var(--border, #243041)',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
      }}
    >
      {/* 1. Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
              VEHICLE JOURNEY — {subject}
            </h3>
            {currentTrajectory && (
              <ConfidenceBadge
                confidence={currentTrajectory.confidence}
                label="Confidence"
              />
            )}
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted, #93a1b2)' }}>
            Correlated by plate. Look-alike variants may be different vehicles. Verify visually.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {trips.length > 1 && (
            <TripSelector
              trips={trips}
              selectedTripId={selectedTripId}
              onSelectTrip={handleTripChange}
            />
          )}

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close journey view"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted, #93a1b2)',
                cursor: 'pointer',
                fontSize: '1.1rem',
                lineHeight: 1,
                padding: '4px',
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Warnings from meta */}
      {warnings.length > 0 && (
        <div
          role="alert"
          style={{
            padding: '6px 10px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            background: 'var(--link-warn-bg, rgba(245, 158, 11, 0.15))',
            color: 'var(--link-warn, #f59e0b)',
            border: '1px solid var(--link-warn, #f59e0b)',
          }}
        >
          ⚠ {warnings.join(', ')}
        </div>
      )}

      {/* 2. Trajectory Tabs if >= 2 */}
      {trajectories.length >= 2 && (
        <TrajectoryTabs
          trajectories={trajectories}
          selectedTrajectoryId={selectedTrajectoryId}
          onSelectTrajectory={setSelectedTrajectoryId}
        />
      )}

      {/* 3. Schematic SVG JourneyMap */}
      <JourneyMap
        trajectory={currentTrajectory}
        topology={topology}
        onSelectCamera={(cam) => {
          const s = currentTrajectory?.sightings.find((s) => s.camera_id === cam);
          if (s && onSelectSighting) {
            onSelectSighting(cam, s.first_seen, s.last_seen);
          }
        }}
      />

      {/* 4. Text Sequence Strip (Always shown, accessible alternative) */}
      {currentTrajectory && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            overflowX: 'auto',
            padding: '10px 12px',
            background: 'var(--bg-panel-2, #18212c)',
            borderRadius: 'var(--radius-sm, 6px)',
            border: '1px solid var(--border-muted, #1c2633)',
          }}
        >
          {currentTrajectory.sightings.map((s, idx) => {
            const link = idx < currentTrajectory.links.length ? currentTrajectory.links[idx] : null;
            const timeStr = new Date(s.first_seen).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return (
              <React.Fragment key={`sighting-${idx}`}>
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectSighting?.(s.camera_id, s.first_seen, s.last_seen)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    cursor: 'pointer',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    background: 'var(--bg-panel, #121821)',
                    border: '1px solid var(--border, #243041)',
                    minWidth: '70px',
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--border-focus, #38bdf8)' }}>
                    {s.camera_id}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted, #93a1b2)' }}>
                    {timeStr}
                  </span>
                </div>

                {link && (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                    <LinkChip link={link} />
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim, #64748b)' }}>
                      +{Math.round(link.gap_s)}s
                    </span>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      )}

      {/* 5. Findings & Anomaly List */}
      <AnomalyList anomalies={correlation?.anomalies ?? []} />
    </div>
  );
};

