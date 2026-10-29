import { z } from 'zod';
import { SeverityEnum, PlateMatchEnum } from '../events/schemas.js';

export const FacetsQuerySchema = z.object({
  camera_id: z.string().optional(),
  event_type: z.string().optional(),
  severity: z.string().optional(),
  min_score: z.coerce.number().min(0).max(100).optional(),
  max_score: z.coerce.number().min(0).max(100).optional(),
  from: z.string().datetime({ offset: true }).optional(),
  to: z.string().datetime({ offset: true }).optional(),
  track_id: z.string().optional(),
  plate: z.string().optional(),
  plate_match: PlateMatchEnum.default('lookalike'),
  vehicle_id: z.string().optional(),
  person_id: z.string().optional(),
  purpose: z.string().optional(),
  time_from: z.string().regex(/^\d{2}:\d{2}$/, 'time_from must be HH:MM').optional(),
  time_to: z.string().regex(/^\d{2}:\d{2}$/, 'time_to must be HH:MM').optional(),
  tz: z.string().optional(),
  q: z.string().optional(),
}).strict();

export const FacetsResponseSchema = z.object({
  data: z.object({
    total: z.number(),
    by_camera: z.array(z.object({ value: z.string(), count: z.number() })),
    by_event_type: z.array(z.object({ value: z.string(), count: z.number() })),
    by_severity: z.object({
      CRITICAL: z.number(),
      HIGH: z.number(),
      MEDIUM: z.number(),
      LOW: z.number(),
    }),
    score_histogram: z.array(z.object({
      from: z.number(),
      to: z.number(),
      count: z.number(),
    })),
    hours: z.array(z.object({
      hour: z.number(),
      count: z.number(),
    })),
  }),
  meta: z.object({
    capped: z.boolean(),
  }),
});
