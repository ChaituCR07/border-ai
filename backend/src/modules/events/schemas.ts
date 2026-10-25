import { z } from 'zod';

export const EventIdSchema = z.string().uuid('event_id must be a valid UUID');

export const SeverityEnum = z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);

export const EventQuerySchema = z.object({
  camera_id: z.string().optional(),
  event_type: z.string().optional(),
  severity: z.string().optional(),
  min_score: z.coerce.number().min(0).max(100).optional(),
  max_score: z.coerce.number().min(0).max(100).optional(),
  from: z.string().datetime({ offset: true }).optional(),
  to: z.string().datetime({ offset: true }).optional(),
  track_id: z.string().optional(),
  plate: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
  cursor: z.string().optional(),
}).strict();

export const EventItemSchema = z.object({
  event_id: z.string().uuid(),
  camera_id: z.string(),
  event_type: z.string(),
  track_id: z.string().nullable(),
  severity: SeverityEnum,
  threat_score: z.number(),
  timestamp: z.string(),
  snapshot_url: z.string().nullable(),
  has_snapshot: z.boolean(),
  snapshot_available: z.boolean(),
  plate: z.string().nullable().optional(),
});

export const EventDetailSchema = EventItemSchema.extend({
  explanation: z.record(z.unknown()).nullable().optional(),
  metadata: z.record(z.unknown()),
  alert: z.object({
    alert_id: z.string(),
    status: z.enum(['OPEN', 'ACKNOWLEDGED', 'RESOLVED']),
    priority: SeverityEnum,
  }).nullable().optional(),
});
