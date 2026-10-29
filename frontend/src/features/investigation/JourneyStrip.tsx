import React, { useEffect, useState } from 'react';

interface Sighting {
  camera_id: string;
  first_seen: string;
  last_seen: string;
  event_count: number;
  max_score: number;
  event_types: string[];
  event_ids: string[];
  plates: string[];
}

interface Transition {
  from: string;
  to: string;
  gap_s: number;
}

interface JourneyData {
  sightings: Sighting[];
  transitions: Transition[];
  total_events: number;
  span_s: number;
  plate_variants: string[];
}

interface JourneyResponse {
  data: JourneyData;
  meta: {
    truncated: boolean;
    total_matching: number;
  };
}

interface JourneyStripProps {
  plate?: string;
  vehicleId?: string;
  onClose: () => void;
  onSelectSighting?: (cameraId: string, from: string, to: string) => void;
  className?: string;
}

export const JourneyStrip: React.FC<JourneyStripProps> = ({
  plate,
  vehicleId,
  onClose,
  onSelectSighting,
  className = '',
}) => {
  const [data, setData] = useState<JourneyData | null>(null);
  const [meta, setMeta] = useState<{ truncated: boolean; total_matching: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!plate && !vehicleId) {
      setData(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    const param = plate ? `plate=${encodeURIComponent(plate)}` : `vehicle_id=${encodeURIComponent(vehicleId!)}`;

    fetch(`/api/investigation/journey?${param}`)
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error?.message || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((json: JourneyResponse) => {
        if (active) {
          setData(json.data);
          setMeta(json.meta);
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
  }, [plate, vehicleId]);

  if (!plate && !vehicleId) return null;

  return (
    <div
      role="region"
      aria-label="Vehicle Journey Sequence"
      className={`bg-slate-900 border border-slate-750 rounded-lg p-3.5 space-y-3 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sky-400 uppercase tracking-wide flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            Journey: {plate ?? vehicleId}
          </span>
          {data && (
            <span className="text-slate-400 font-mono text-[11px]">
              ({data.sightings.length} sightings · span {Math.round(data.span_s)}s · {data.total_events} events)
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close journey"
          className="text-slate-400 hover:text-slate-100 p-1"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {loading && (
        <div className="py-4 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
          <div className="w-4 h-4 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
          Reconstructing journey...
        </div>
      )}

      {error && (
        <div className="p-2 text-xs text-red-300 bg-red-950/40 rounded border border-red-800/40">
          {error}
        </div>
      )}

      {/* OCR Variants Banner */}
      {data && data.plate_variants.length > 1 && (
        <div className="flex items-center gap-2 p-2 bg-amber-950/30 border border-amber-800/40 rounded text-xs text-amber-200">
          <span className="font-semibold text-amber-300">OCR Variants:</span>
          <div className="flex flex-wrap gap-1.5">
            {data.plate_variants.map((variant) => (
              <span key={variant} className="font-mono bg-amber-900/40 px-1.5 py-0.5 rounded text-[11px]">
                {variant}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sightings & Transitions Sequence */}
      {data && (
        <div className="flex items-center overflow-x-auto py-2 gap-2">
          {data.sightings.map((s, idx) => {
            const nextTransition = data.transitions[idx];

            return (
              <React.Fragment key={idx}>
                {/* Sighting Card */}
                <div
                  onClick={() => onSelectSighting?.(s.camera_id, s.first_seen, s.last_seen)}
                  className="shrink-0 w-44 bg-slate-950/80 hover:bg-slate-800/80 border border-slate-750 hover:border-sky-500/60 rounded-lg p-2.5 cursor-pointer transition-all space-y-1"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-sky-400">{s.camera_id}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded font-mono font-bold text-[10px] ${
                        s.max_score >= 80 ? 'bg-red-950 text-red-300' : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {s.max_score}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-300 font-mono">
                    {new Date(s.first_seen).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>

                  <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-850">
                    <span>{s.event_count} events</span>
                    {s.plates.length > 0 && <span className="font-mono">{s.plates[0]}</span>}
                  </div>
                </div>

                {/* Transition Gap Arrow */}
                {nextTransition && (
                  <div className="shrink-0 flex flex-col items-center justify-center px-1 text-slate-500">
                    <span className="text-[10px] font-mono text-sky-400 font-semibold mb-0.5">
                      {`+${Math.round(nextTransition.gap_s)}s`}
                    </span>
                    <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      )}

      {meta?.truncated && (
        <div className="text-center text-[11px] text-amber-400 italic">
          Journey capped at 5,000 events. Narrow your time window for complete fidelity.
        </div>
      )}
    </div>
  );
};
