import { z } from 'zod';

export const Severity = z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']);
export type Severity = z.infer<typeof Severity>;

export const AlertEvent = z.object({
  camera_id: z.string().min(1),
  event_type: z.string().min(1),
  threat_score: z.number().int().min(0).max(100),
  plate: z.string().nullable(),
  timestamp: z.string().datetime({ offset: true }),
  snapshot_url: z.string().nullable(),
  snapshot_available: z.boolean(),
}).strict();
export type AlertEvent = z.infer<typeof AlertEvent>;

export const AlertView = z.object({
  alert_id: z.string().uuid(),
  event_id: z.string().uuid(),
  priority: Severity,
  status: z.enum(['OPEN', 'ACKNOWLEDGED', 'RESOLVED']),
  acknowledged_by: z.string().nullable(),
  acknowledged_at: z.string().datetime({ offset: true }).nullable(),
  created_at: z.string().datetime({ offset: true }),
  persisted: z.boolean(),
  event: AlertEvent,
}).strict();
export type AlertView = z.infer<typeof AlertView>;

const base = { v: z.literal(1) };

export const ServerMessage = z.discriminatedUnion('type', [
  z.object({
    ...base,
    type: z.literal('hello'),
    server_epoch: z.string().uuid(),
    seq: z.number().int().min(0),
    server_time: z.string().datetime({ offset: true }),
  }),
  z.object({
    ...base,
    type: z.literal('heartbeat'),
    seq: z.number().int().min(0),
    server_time: z.string().datetime({ offset: true }),
  }),
  z.object({
    ...base,
    type: z.literal('alert.created'),
    seq: z.number().int().min(1),
    data: z.object({
      alert: AlertView,
    }),
  }),
  z.object({
    ...base,
    type: z.literal('alert.updated'),
    seq: z.number().int().min(1),
    data: z.object({
      alert: AlertView,
    }),
  }),
  z.object({
    ...base,
    type: z.literal('resync_required'),
    seq: z.number().int().min(0),
    reason: z.string(),
  }),
]);
export type ServerMessage = z.infer<typeof ServerMessage>;

export const ClientMessage = z.discriminatedUnion('type', [
  z.object({
    ...base,
    type: z.literal('ping'),
  }),
]);
export type ClientMessage = z.infer<typeof ClientMessage>;

// Standard Close Codes
export const WS_CLOSE = {
  NORMAL: 1000,
  GOING_AWAY: 1001,
  POLICY: 1008,
  TOO_BIG: 1009,
  TRY_AGAIN: 1013,
} as const;

export function makeAlertView(overrides?: Partial<AlertView>): AlertView {
  return {
    alert_id: '9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d',
    event_id: '11111111-1111-1111-1111-111111111111',
    priority: 'CRITICAL',
    status: 'OPEN',
    acknowledged_by: null,
    acknowledged_at: null,
    created_at: '2026-10-27T12:00:00.000000Z',
    persisted: true,
    event: {
      camera_id: 'CAM-03',
      event_type: 'RESTRICTED_ZONE_ENTRY',
      threat_score: 92,
      plate: 'KA01AB1234',
      timestamp: '2026-10-27T12:00:00.000000Z',
      snapshot_url: '/api/snapshots/CAM-03/snap.jpg',
      snapshot_available: true,
    },
    ...overrides,
  };
}
