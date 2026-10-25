import { z } from 'zod';
import { SeverityEnum } from '../events/schemas.js';

export const AlertIdSchema = z.string().uuid('alert_id must be a valid UUID');
export const AlertStatusEnum = z.enum(['OPEN', 'ACKNOWLEDGED', 'RESOLVED']);

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

export const AlertResourceSchema = z.object({
  alert_id: z.string().uuid(),
  event_id: z.string().uuid(),
  priority: SeverityEnum,
  status: AlertStatusEnum,
  acknowledged_by: z.string().nullable(),
  acknowledged_at: z.string().nullable(),
  created_at: z.string(),
  event: z.object({
    camera_id: z.string(),
    event_type: z.string(),
    threat_score: z.number(),
    plate: z.string().nullable().optional(),
    snapshot_url: z.string().nullable(),
  }),
});
