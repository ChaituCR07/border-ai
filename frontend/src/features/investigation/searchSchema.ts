export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type PlateMatch = 'exact' | 'lookalike' | 'prefix' | 'contains';
export type SortOption = 'time' | 'score';
export type ViewOption = 'table' | 'timeline';

export interface InvestigationSearchState {
  q?: string;
  camera_id?: string[];
  event_type?: string[];
  severity?: Severity[];
  min_score?: number;
  max_score?: number;
  from?: string;
  to?: string;
  plate?: string;
  plate_match?: PlateMatch;
  vehicle_id?: string;
  person_id?: string;
  time_from?: string;
  time_to?: string;
  tz?: string;
  sort?: SortOption;
  view?: ViewOption;
  selected_event_id?: string;
}

export function getDefaultTimeRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to.getTime() - 24 * 3600 * 1000);
  return {
    from: from.toISOString(),
    to: to.toISOString(),
  };
}

export function getDefaultSearchState(): InvestigationSearchState {
  const range = getDefaultTimeRange();
  return {
    ...range,
    sort: 'time',
    view: 'table',
    plate_match: 'lookalike',
  };
}

export function parseSearchParams(params: URLSearchParams): InvestigationSearchState {
  const state: InvestigationSearchState = {};

  const q = params.get('q');
  if (q) state.q = q;

  const cam = params.get('camera_id');
  if (cam) {
    const list = cam.split(',').map(s => s.trim()).filter(Boolean);
    if (list.length > 0) state.camera_id = list;
  }

  const type = params.get('event_type');
  if (type) {
    const list = type.split(',').map(s => s.trim()).filter(Boolean);
    if (list.length > 0) state.event_type = list;
  }

  const sev = params.get('severity');
  if (sev) {
    const valid = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
    const list = sev.split(',').map(s => s.trim().toUpperCase()).filter(s => valid.includes(s)) as Severity[];
    if (list.length > 0) state.severity = list;
  }

  const minScore = params.get('min_score');
  if (minScore !== null && !isNaN(Number(minScore))) {
    state.min_score = Math.max(0, Math.min(100, Number(minScore)));
  }

  const maxScore = params.get('max_score');
  if (maxScore !== null && !isNaN(Number(maxScore))) {
    state.max_score = Math.max(0, Math.min(100, Number(maxScore)));
  }

  const from = params.get('from');
  if (from) state.from = from;

  const to = params.get('to');
  if (to) state.to = to;

  const plate = params.get('plate');
  if (plate) state.plate = plate;

  const plateMatch = params.get('plate_match');
  if (plateMatch && ['exact', 'lookalike', 'prefix', 'contains'].includes(plateMatch)) {
    state.plate_match = plateMatch as PlateMatch;
  }

  const vehicleId = params.get('vehicle_id');
  if (vehicleId) state.vehicle_id = vehicleId;

  const personId = params.get('person_id');
  if (personId) state.person_id = personId;

  const timeFrom = params.get('time_from');
  if (timeFrom && /^\d{2}:\d{2}$/.test(timeFrom)) state.time_from = timeFrom;

  const timeTo = params.get('time_to');
  if (timeTo && /^\d{2}:\d{2}$/.test(timeTo)) state.time_to = timeTo;

  const tz = params.get('tz');
  if (tz) state.tz = tz;

  const sort = params.get('sort');
  if (sort === 'score' || sort === 'time') state.sort = sort;

  const view = params.get('view');
  if (view === 'timeline' || view === 'table') state.view = view;

  const selectedEvent = params.get('selected_event_id');
  if (selectedEvent) state.selected_event_id = selectedEvent;

  return state;
}

export function serializeSearchParams(state: InvestigationSearchState): URLSearchParams {
  const params = new URLSearchParams();

  if (state.q) params.set('q', state.q);
  if (state.camera_id && state.camera_id.length > 0) params.set('camera_id', state.camera_id.join(','));
  if (state.event_type && state.event_type.length > 0) params.set('event_type', state.event_type.join(','));
  if (state.severity && state.severity.length > 0) params.set('severity', state.severity.join(','));
  if (state.min_score !== undefined) params.set('min_score', String(state.min_score));
  if (state.max_score !== undefined) params.set('max_score', String(state.max_score));
  if (state.from) params.set('from', state.from);
  if (state.to) params.set('to', state.to);
  if (state.plate) params.set('plate', state.plate);
  if (state.plate_match && state.plate_match !== 'lookalike') params.set('plate_match', state.plate_match);
  if (state.vehicle_id) params.set('vehicle_id', state.vehicle_id);
  if (state.person_id) params.set('person_id', state.person_id);
  if (state.time_from) params.set('time_from', state.time_from);
  if (state.time_to) params.set('time_to', state.time_to);
  if (state.tz && state.tz !== 'UTC') params.set('tz', state.tz);
  if (state.sort && state.sort !== 'time') params.set('sort', state.sort);
  if (state.view && state.view !== 'table') params.set('view', state.view);
  if (state.selected_event_id) params.set('selected_event_id', state.selected_event_id);

  // Notice: 'purpose' is NEVER serialized to the URL (privacy requirement ADR 0024 / ADR 0025)
  return params;
}
