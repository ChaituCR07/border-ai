import { z } from 'zod';
import { SeverityEnum } from '../events/schemas.js';

export const AlertIdSchema = z.string().uuid('alert_id must be a valid UUID');
export const AlertStatusEnum = z.enum(['OPEN', 'ACKNOWLEDGED', 'RESOLVED']);
export const ResolutionEnum = z.enum(['TRUE_POSITIVE', 'FALSE_POSITIVE', 'DUPLICATE', 'OTHER']);

export const AlertQuerySchema = z.object({
  status: AlertStatusEnum.optional(),
  priority: SeverityEnum.optional(),
  camera_id: z.string().optional(),
  from: z.string().datetime({ offset: true }).optional(),
  to: z.string().datetime({ offset: true }).optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
  cursor: z.string().optional(),
}).strict();

export const AcknowledgeBodySchema = z.object({
  acknowledged_by: z.string().max(64).optional(),
}).strict();

export const ResolveBodySchema = z.object({
  resolution: ResolutionEnum,
  note: z.string().max(500, 'Resolution note must be at most 500 characters').optional(),
}).strict();

export const AlertResourceSchema = z.object({
  alert_id: z.string().uuid(),
  event_id: z.string().uuid(),
  priority: SeverityEnum,
  status: AlertStatusEnum,
  acknowledged_by: z.string().nullable(),
  acknowledged_at: z.string().nullable(),
  resolved_by: z.string().nullable().optional(),
  resolved_at: z.string().nullable().optional(),
  resolution: ResolutionEnum.nullable().optional(),
  created_at: z.string(),
  received_at: z.string().optional(),
  event: z.object({
    camera_id: z.string(),
    event_type: z.string(),
    threat_score: z.number(),
    plate: z.string().nullable().optional(),
    snapshot_url: z.string().nullable(),
  }),
});

export const NotificationItemSchema = z.object({
  notification_id: z.string().uuid(),
  kind: z.string(),
  recipient: z.string(),
  status: z.string(),
  sent_at: z.string().nullable().optional(),
});

export const AlertDetailSchema = AlertResourceSchema.extend({
  explanation: z.array(z.object({
    name: z.string(),
    points: z.number(),
    detail: z.string().optional(),
  })).optional(),
  notifications: z.object({
    sent: z.number().int().nonnegative(),
    pending: z.number().int().nonnegative(),
    skipped: z.number().int().nonnegative(),
    failed: z.number().int().nonnegative(),
    items: z.array(NotificationItemSchema).optional(),
  }),
});

