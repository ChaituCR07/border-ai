import type { InvestigationSearchState, Severity, PlateMatch } from './searchSchema.js';

export interface ParsedQuery {
  tokens: { key: string; value: string; raw: string }[];
  freeText: string;
  state: Partial<InvestigationSearchState>;
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PLATE_REGEX = /^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$/i;

export function parseOmniboxQuery(text: string): ParsedQuery {
  const trimmed = text.trim();
  if (!trimmed) {
    return { tokens: [], freeText: '', state: {} };
  }

  const parts = trimmed.split(/\s+/);
  const tokens: { key: string; value: string; raw: string }[] = [];
  const freeWords: string[] = [];
  const state: Partial<InvestigationSearchState> = {};

  const cameras: string[] = [];
  const types: string[] = [];
  const severities: Severity[] = [];

  for (const part of parts) {
    const match = /^([a-zA-Z_]+):(.+)$/.exec(part);
    if (match && match[1] && match[2]) {
      const key = match[1].toLowerCase();
      const val = match[2];

      if (key === 'cam' || key === 'camera') {
        const list = val.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
        cameras.push(...list);
        tokens.push({ key: 'camera', value: list.join(','), raw: part });
        continue;
      }

      if (key === 'type') {
        const list = val.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
        types.push(...list);
        tokens.push({ key: 'type', value: list.join(','), raw: part });
        continue;
      }

      if (key === 'sev' || key === 'severity') {
        const list = val.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
        for (const s of list) {
          if (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].includes(s)) {
            severities.push(s as Severity);
          }
        }
        tokens.push({ key: 'severity', value: list.join(','), raw: part });
        continue;
      }

      if (key === 'score') {
        tokens.push({ key: 'score', value: val, raw: part });
        if (val.startsWith('>=')) {
          state.min_score = Number(val.slice(2));
        } else if (val.startsWith('>')) {
          state.min_score = Number(val.slice(1)) + 1;
        } else if (val.startsWith('<=')) {
          state.max_score = Number(val.slice(2));
        } else if (val.startsWith('<')) {
          state.max_score = Number(val.slice(1)) - 1;
        } else if (val.includes('-')) {
          const [min, max] = val.split('-').map(Number);
          if (!isNaN(min!)) state.min_score = min;
          if (!isNaN(max!)) state.max_score = max;
        } else if (!isNaN(Number(val))) {
          state.min_score = Number(val);
        }
        continue;
      }

      if (key === 'plate') {
        tokens.push({ key: 'plate', value: val, raw: part });
        if (val.endsWith('*')) {
          state.plate = val.slice(0, -1);
          state.plate_match = 'prefix';
        } else if (val.startsWith('*') && val.endsWith('*')) {
          state.plate = val.slice(1, -1);
          state.plate_match = 'contains';
        } else {
          state.plate = val;
        }
        continue;
      }

      if (key === 'vehicle' || key === 'veh') {
        tokens.push({ key: 'vehicle', value: val, raw: part });
        state.vehicle_id = val;
        continue;
      }

      if (key === 'person' || key === 'per') {
        tokens.push({ key: 'person', value: val, raw: part });
        state.person_id = val;
        continue;
      }
    }

    freeWords.push(part);
  }

  if (cameras.length > 0) state.camera_id = cameras;
  if (types.length > 0) state.event_type = types;
  if (severities.length > 0) state.severity = severities;

  const freeText = freeWords.join(' ');
  if (freeWords.length === 1 && freeWords[0]) {
    const single = freeWords[0];
    if (UUID_REGEX.test(single)) {
      state.selected_event_id = single;
    } else if (PLATE_REGEX.test(single)) {
      state.plate = single.toUpperCase();
      state.plate_match = 'lookalike';
    } else {
      state.q = freeText;
    }
  } else if (freeText) {
    state.q = freeText;
  }

  return { tokens, freeText, state };
}

export function formatQueryTokens(state: InvestigationSearchState): string {
  const parts: string[] = [];

  if (state.camera_id && state.camera_id.length > 0) {
    parts.push(`cam:${state.camera_id.join(',')}`);
  }
  if (state.event_type && state.event_type.length > 0) {
    parts.push(`type:${state.event_type.join(',')}`);
  }
  if (state.severity && state.severity.length > 0) {
    parts.push(`sev:${state.severity.join(',')}`);
  }
  if (state.min_score !== undefined && state.max_score !== undefined) {
    parts.push(`score:${state.min_score}-${state.max_score}`);
  } else if (state.min_score !== undefined) {
    parts.push(`score:>=${state.min_score}`);
  } else if (state.max_score !== undefined) {
    parts.push(`score:<=${state.max_score}`);
  }
  if (state.plate) {
    if (state.plate_match === 'prefix') {
      parts.push(`plate:${state.plate}*`);
    } else if (state.plate_match === 'contains') {
      parts.push(`plate:*${state.plate}*`);
    } else {
      parts.push(`plate:${state.plate}`);
    }
  }
  if (state.vehicle_id) {
    parts.push(`vehicle:${state.vehicle_id}`);
  }
  if (state.person_id) {
    parts.push(`person:${state.person_id}`);
  }
  if (state.q) {
    parts.push(state.q);
  }

  return parts.join(' ');
}
