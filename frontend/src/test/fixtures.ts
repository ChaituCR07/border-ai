import type { CameraResource, AlertResource, EventItem, ThreatSummary } from '../api/types';

export function makeCamera(overrides?: Partial<CameraResource>): CameraResource {
  return {
    camera_id: 'CAM-01',
    name: 'North Gate East',
    location_label: 'Sector 4, Km 12',
    stream_url: 'rtsp://10.0.4.23:554/live',
    has_credentials: true,
    credentials_ref: 'CAM_01_CREDS',
    enabled: true,
    live_view_url: 'http://localhost:8001/cam/CAM-01.mjpg',
    created_at: '2026-10-25T08:00:00.000000Z',
    updated_at: '2026-10-25T08:00:00.000000Z',
    ...overrides,
  };
}

export function makeAlert(overrides?: Partial<AlertResource>): AlertResource {
  return {
    alert_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    event_id: '11111111-1111-1111-1111-111111111111',
    priority: 'CRITICAL',
    status: 'OPEN',
    acknowledged_by: null,
    acknowledged_at: null,
    created_at: '2026-10-26T12:00:00.000000Z',
    event: {
      camera_id: 'CAM-01',
      event_type: 'RESTRICTED_ZONE_ENTRY',
      threat_score: 95,
      plate: 'KA01AB1234',
      snapshot_url: '/api/snapshots/CAM-01/snap1.jpg',
    },
    ...overrides,
  };
}

export function makeEvent(overrides?: Partial<EventItem>): EventItem {
  return {
    event_id: '11111111-1111-1111-1111-111111111111',
    camera_id: 'CAM-01',
    event_type: 'RESTRICTED_ZONE_ENTRY',
    track_id: '42',
    severity: 'CRITICAL',
    threat_score: 95,
    timestamp: '2026-10-26T12:00:00.000000Z',
    snapshot_url: '/api/snapshots/CAM-01/snap1.jpg',
    has_snapshot: true,
    snapshot_available: true,
    plate: 'KA01AB1234',
    ...overrides,
  };
}

export function makeThreatSummary(): ThreatSummary {
  return {
    severity_counts: {
      CRITICAL: 5,
      HIGH: 12,
      MEDIUM: 28,
      LOW: 94,
    },
    open_alerts_by_priority: {
      CRITICAL: 2,
      HIGH: 7,
      MEDIUM: 21,
      LOW: 84,
    },
    score_histogram: [
      { from: 0, to: 9, count: 40 },
      { from: 10, to: 19, count: 30 },
      { from: 20, to: 29, count: 24 },
      { from: 30, to: 39, count: 18 },
      { from: 40, to: 49, count: 10 },
      { from: 50, to: 59, count: 6 },
      { from: 60, to: 69, count: 7 },
      { from: 70, to: 79, count: 5 },
      { from: 80, to: 89, count: 2 },
      { from: 90, to: 100, count: 3 },
    ],
    top_event_types: [
      { event_type: 'LINE_CROSSING', count: 35 },
      { event_type: 'RESTRICTED_ZONE_ENTRY', count: 18 },
    ],
    top_plates: [
      { plate: 'KA01AB1234', events: 6, max_score: 95 },
      { plate: 'MH12DE1433', events: 4, max_score: 75 },
    ],
  };
}
