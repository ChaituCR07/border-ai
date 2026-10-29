import React from 'react';
import type { InvestigationSearchState, Severity, PlateMatch } from './searchSchema.js';
import { FacetList } from './FacetList.js';

export interface FacetsData {
  total: number;
  by_camera: { value: string; count: number }[];
  by_event_type: { value: string; count: number }[];
  by_severity: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  score_histogram?: { from: number; to: number; count: number }[];
  hours?: { hour: number; count: number }[];
}

interface FilterPanelProps {
  state: InvestigationSearchState;
  facets?: FacetsData | null;
  loadingFacets?: boolean;
  onPatchState: (patch: Partial<InvestigationSearchState>) => void;
  onReset: () => void;
  className?: string;
  userRole?: string;
}

const SEVERITIES: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

const SEVERITY_COLORS: Record<Severity, { active: string; inactive: string }> = {
  CRITICAL: {
    active: 'bg-red-900/60 text-red-200 border-red-500',
    inactive: 'bg-slate-900 text-slate-400 border-slate-750 hover:border-slate-600',
  },
  HIGH: {
    active: 'bg-orange-900/60 text-orange-200 border-orange-500',
    inactive: 'bg-slate-900 text-slate-400 border-slate-750 hover:border-slate-600',
  },
  MEDIUM: {
    active: 'bg-yellow-900/60 text-yellow-200 border-yellow-500',
    inactive: 'bg-slate-900 text-slate-400 border-slate-750 hover:border-slate-600',
  },
  LOW: {
    active: 'bg-blue-900/60 text-blue-200 border-blue-500',
    inactive: 'bg-slate-900 text-slate-400 border-slate-750 hover:border-slate-600',
  },
};

export const FilterPanel: React.FC<FilterPanelProps> = ({
  state,
  facets,
  loadingFacets = false,
  onPatchState,
  onReset,
  className = '',
  userRole,
}) => {
  const isInvestigator = userRole === 'INVESTIGATOR' || userRole === 'ADMIN';

  const applyTimePreset = (hours: number) => {
    const to = new Date();
    const from = new Date(to.getTime() - hours * 3600 * 1000);
    onPatchState({ from: from.toISOString(), to: to.toISOString() });
  };

  const toggleSeverity = (sev: Severity) => {
    const current = state.severity ?? [];
    if (current.includes(sev)) {
      onPatchState({ severity: current.filter(s => s !== sev) });
    } else {
      onPatchState({ severity: [...current, sev] });
    }
  };

  return (
    <div className={`bg-slate-900/90 border border-slate-800 rounded-lg p-4 space-y-5 text-sm ${className}`}>
      {/* Header with Total and Reset */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Filters</span>
          {facets && (
            <span className="ml-2 text-xs text-sky-400 font-mono">
              ({facets.total.toLocaleString()} matching)
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onReset}
          className="text-xs text-slate-400 hover:text-slate-200 underline"
        >
          Reset All
        </button>
      </div>

      {/* Time Presets */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Time Range</label>
        <div className="grid grid-cols-3 gap-1.5">
          <button
            type="button"
            onClick={() => applyTimePreset(1)}
            className="px-2 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            Last 1h
          </button>
          <button
            type="button"
            onClick={() => applyTimePreset(24)}
            className="px-2 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            Last 24h
          </button>
          <button
            type="button"
            onClick={() => applyTimePreset(168)}
            className="px-2 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            Last 7d
          </button>
        </div>
      </div>

      {/* Plate Matching Mode */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Plate Matching</label>
        <div className="grid grid-cols-2 gap-1.5">
          {(['lookalike', 'exact', 'prefix', 'contains'] as PlateMatch[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onPatchState({ plate_match: mode })}
              className={`px-2 py-1 text-xs font-medium rounded border transition-colors capitalize ${
                (state.plate_match ?? 'lookalike') === mode
                  ? 'bg-sky-900/50 text-sky-200 border-sky-500'
                  : 'bg-slate-900 text-slate-400 border-slate-750 hover:border-slate-700'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Severity Badges */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Severity</label>
        <div className="grid grid-cols-2 gap-1.5">
          {SEVERITIES.map((sev) => {
            const isSelected = (state.severity ?? []).includes(sev);
            const count = facets?.by_severity?.[sev] ?? 0;
            const style = isSelected ? SEVERITY_COLORS[sev].active : SEVERITY_COLORS[sev].inactive;
            return (
              <button
                key={sev}
                type="button"
                onClick={() => toggleSeverity(sev)}
                className={`flex items-center justify-between px-2.5 py-1 rounded text-xs border font-medium ${style}`}
              >
                <span>{sev}</span>
                <span className="ml-1 opacity-75 font-mono">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Camera Facet List */}
      <FacetList
        title="Cameras"
        items={facets?.by_camera ?? []}
        selected={state.camera_id ?? []}
        onChange={(cams) => onPatchState({ camera_id: cams.length ? cams : undefined })}
      />

      {/* Event Type Facet List */}
      <FacetList
        title="Event Types"
        items={facets?.by_event_type ?? []}
        selected={state.event_type ?? []}
        onChange={(types) => onPatchState({ event_type: types.length ? types : undefined })}
      />

      {/* Threat Score Range */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Threat Score (0–100)</label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={100}
            value={state.min_score ?? ''}
            onChange={(e) => onPatchState({ min_score: e.target.value ? Number(e.target.value) : undefined })}
            placeholder="Min"
            className="w-full text-xs px-2 py-1 bg-slate-900 border border-slate-750 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          <span className="text-slate-500 text-xs">to</span>
          <input
            type="number"
            min={0}
            max={100}
            value={state.max_score ?? ''}
            onChange={(e) => onPatchState({ max_score: e.target.value ? Number(e.target.value) : undefined })}
            placeholder="Max"
            className="w-full text-xs px-2 py-1 bg-slate-900 border border-slate-750 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {/* Time-of-Day Window */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Time of Day (HH:MM)</label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            pattern="\\d{2}:\\d{2}"
            placeholder="22:00"
            value={state.time_from ?? ''}
            onChange={(e) => onPatchState({ time_from: e.target.value || undefined })}
            className="w-full text-xs px-2 py-1 bg-slate-900 border border-slate-750 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          <span className="text-slate-500 text-xs">to</span>
          <input
            type="text"
            pattern="\\d{2}:\\d{2}"
            placeholder="05:00"
            value={state.time_to ?? ''}
            onChange={(e) => onPatchState({ time_to: e.target.value || undefined })}
            className="w-full text-xs px-2 py-1 bg-slate-900 border border-slate-750 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {/* Person ID (Investigator Only) */}
      {isInvestigator && (
        <div className="space-y-1.5 pt-2 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Person Identifier</label>
            <span className="text-[10px] text-amber-400 bg-amber-950/60 px-1 py-0.5 rounded border border-amber-800/40">
              Investigator
            </span>
          </div>
          <input
            type="text"
            value={state.person_id ?? ''}
            onChange={(e) => onPatchState({ person_id: e.target.value || undefined })}
            placeholder="e.g. PER-1002"
            className="w-full text-xs px-2 py-1 bg-slate-900 border border-slate-750 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          <p className="text-[10px] text-slate-500 leading-tight">
            Person searches require an explicit investigative purpose and are fully audit-logged.
          </p>
        </div>
      )}
    </div>
  );
};
