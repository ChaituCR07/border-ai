import React from 'react';
import { useJourney } from './api.js';

export interface JourneySoFarProps {
  plate: string;
  timestamp: string;
  currentCameraId: string;
  onViewFullJourney?: () => void;
  className?: string;
}

export const JourneySoFar: React.FC<JourneySoFarProps> = ({
  plate,
  timestamp,
  currentCameraId,
  onViewFullJourney,
  className = '',
}) => {
  const { data, isLoading, isError } = useJourney({
    plate,
    end_at: timestamp,
    correlate: true,
  });

  if (isLoading) {
    return (
      <div className={`text-xs text-slate-500 py-1 ${className}`}>
        Loading journey so far...
      </div>
    );
  }

  if (isError || !data?.data) {
    return null; // Silent degradation: failure never blocks event drawer
  }

  const correlation = data.data.correlation;
  const latestTrip = correlation?.trips?.at(-1);
  const trajectory = latestTrip?.trajectories?.[0];
  const sightings = trajectory?.sightings ?? data.data.sightings ?? [];
  const warnings = correlation?.anomalies?.filter((a) => a.severity === 'warning') ?? [];

  if (sightings.length <= 1 && warnings.length === 0) {
    return null; // First sighting of the day with no anomalies
  }

  return (
    <div
      className={`journey-so-far p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2 ${className}`}
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-300">Journey so far</span>
        {onViewFullJourney && (
          <button
            type="button"
            onClick={onViewFullJourney}
            className="text-sky-400 hover:text-sky-300 font-medium hover:underline text-[11px]"
          >
            Open full journey →
          </button>
        )}
      </div>

      {/* Warning anomaly hint */}
      {warnings.length > 0 && (
        <div className="text-[11px] text-amber-300 bg-amber-950/40 border border-amber-800/60 rounded px-2 py-1 flex items-center gap-1.5">
          <span>⚠</span>
          <span>{warnings[0]!.message}</span>
        </div>
      )}

      {/* Compact text sequence */}
      <div className="text-xs text-slate-300 flex items-center flex-wrap gap-1.5">
        <span className="text-slate-400 text-[11px]">Earlier:</span>
        {sightings.map((s, idx) => {
          const isCurrent = s.camera_id === currentCameraId && idx === sightings.length - 1;
          const time = new Date(s.first_seen).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          });

          return (
            <React.Fragment key={idx}>
              {idx > 0 && <span className="text-slate-600">→</span>}
              <span
                className={`px-1.5 py-0.5 rounded text-[11px] ${
                  isCurrent
                    ? 'bg-sky-950 text-sky-200 border border-sky-800/80 font-bold'
                    : 'bg-slate-900 text-slate-300 border border-slate-800'
                }`}
              >
                {s.camera_id} {time} {isCurrent && '(this alert)'}
              </span>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
