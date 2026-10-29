export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
export type WatchlistEntityType = 'VEHICLE' | 'PERSON';
export type WatchlistRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type Role = 'ADMIN' | 'OPERATOR' | 'INVESTIGATOR' | 'VIEWER';

export interface Actor {
  id: string;
  role: Role;
}

export interface CameraResource {
  camera_id: string;
  name: string | null;
  location_label: string | null;
  stream_url: string | null;
  has_credentials: boolean;
  credentials_ref: string | null;
  enabled: boolean;
  live_view_url: string;
  created_at: string;
  updated_at: string;
}

export interface EventResource {
  event_id: string;
  camera_id: string;
  event_type: string;
  track_id: string | null;
  severity: Severity;
  threat_score: number;
  timestamp: string;
  snapshot_url: string | null;
  has_snapshot: boolean;
  snapshot_available: boolean;
  plate?: string | null;
  plate_match?: 'exact' | 'lookalike' | 'prefix' | 'partial' | null;
  vehicle_id?: string | null;
  person_id?: string | null;
}

export interface EventDetailResource extends EventResource {
  explanation?: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  alert?: {
    alert_id: string;
    status: AlertStatus;
    priority: Severity;
  } | null;
}

export interface AlertResource {
  alert_id: string;
  event_id: string;
  priority: Severity;
  status: AlertStatus;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
  event: {
    camera_id: string;
    event_type: string;
    threat_score: number;
    plate?: string | null;
    snapshot_url: string | null;
  };
}

export interface WatchlistResource {
  entity_id: string;
  entity_type: WatchlistEntityType;
  identifier: string;
  name: string;
  risk_level: WatchlistRiskLevel;
  notes: string | null;
  consent_reference: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}
