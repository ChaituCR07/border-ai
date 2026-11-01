export type LinkClass =
  | 'REVISIT'
  | 'PLAUSIBLE'
  | 'FAST'
  | 'SLOW'
  | 'IMPOSSIBLE'
  | 'SIMULTANEOUS'
  | 'OVERLAP_OK'
  | 'UNLINKED';

export interface Factor {
  name: 'plate' | 'timing' | 'appearance';
  value: number;
  detail: string;
}

export interface Link {
  from_camera: string;
  to_camera: string;
  gap_s: number;
  class: LinkClass;
  confidence: number;
  factors: Factor[];
  expected: { min_s: number; typical_s: number; max_s: number } | null;
  missed_cameras: string[];
}

export interface Sighting {
  camera_id: string;
  first_seen: string;
  last_seen: string;
  event_count: number;
  max_score: number;
  event_types: string[];
  event_ids: string[];
  plates: string[];
}

export interface Transition {
  from: string;
  to: string;
  gap_s: number;
}

export interface Trajectory {
  id: string;
  sightings: Sighting[];
  links: Link[];
  confidence: number;
  mean_confidence: number;
  cameras: string[];
}

export interface Trip {
  trip_id: string;
  start: string;
  end: string;
  trajectories: Trajectory[];
}

export type AnomalyType =
  | 'IMPOSSIBLE_TRAVEL'
  | 'SIMULTANEOUS_SIGHTINGS'
  | 'MULTIPLE_TRAJECTORIES'
  | 'MISSED_CAMERA'
  | 'SLOW_TRANSIT'
  | 'FAST_TRANSIT'
  | 'UNLINKED_HOP'
  | 'TRAJECTORY_OVERFLOW';

export interface Anomaly {
  type: AnomalyType;
  severity: 'info' | 'warning';
  trip_id: string;
  trajectory_ids: string[];
  message: string;
  evidence: Record<string, any>;
}

export interface CorrelationData {
  topology_version: string;
  config_version: number;
  trips: Trip[];
  anomalies: Anomaly[];
}

export interface JourneyData {
  sightings: Sighting[];
  transitions: Transition[];
  total_events: number;
  span_s: number;
  plate_variants: string[];
}

export interface JourneyResponse {
  data: {
    journey?: JourneyData;
    correlation?: CorrelationData;
    sightings?: Sighting[];
    transitions?: Transition[];
    total_events?: number;
    span_s?: number;
    plate_variants?: string[];
  };
  meta: {
    truncated: boolean;
    total_matching: number;
    warnings?: string[];
  };
}

export interface TopologyCamera {
  camera_id: string;
  name: string;
  location_label: string;
  map_x: number;
  map_y: number;
}

export interface TopologyLink {
  a: string;
  b: string;
  min_s: number;
  typical_s: number;
  max_s: number;
  direction?: 'both' | 'a_to_b';
  overlap?: boolean;
}

export interface TopologyData {
  version: string;
  cameras: TopologyCamera[];
  links: TopologyLink[];
}

export interface SequenceHop {
  camera_id: string;
  timestamp: string;
  event_id: string;
}

export interface SequenceMatch {
  plate_key: string;
  representative_plate: string;
  plate_variants: string[];
  hops: SequenceHop[];
  total_duration_s: number;
}

export interface SequenceSearchResponse {
  data: SequenceMatch[];
  meta: {
    steps: number;
    cameras: string[];
    total: number;
    limit: number;
  };
}
