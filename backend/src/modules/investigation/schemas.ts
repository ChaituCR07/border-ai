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

export const SuggestQuerySchema = z.object({
  kind: z.enum(['plate', 'camera', 'person']),
  prefix: z.string().min(1).max(32),
  limit: z.coerce.number().int().min(1).max(20).default(10),
});

export const SuggestResponseSchema = z.object({
  data: z.array(
    z.object({
      value: z.string(),
      count: z.number(),
      last_seen: z.string(),
    })
  ),
});

export const JourneyQuerySchema = z.object({
  plate: z.string().min(2).max(16).optional(),
  vehicle_id: z.string().min(1).max(64).optional(),
  from: z.string().datetime({ offset: true }).optional(),
  to: z.string().datetime({ offset: true }).optional(),
  end_at: z.string().datetime({ offset: true }).optional(),
  correlate: z.preprocess((val) => {
    if (typeof val === 'string') {
      if (val.toLowerCase() === 'false' || val === '0') return false;
      if (val.toLowerCase() === 'true' || val === '1') return true;
    }
    return val;
  }, z.boolean().default(true)),
}).strict().refine(
  data => (data.plate && !data.vehicle_id) || (!data.plate && data.vehicle_id),
  {
    message: 'Exactly one of plate or vehicle_id must be provided',
    path: ['plate'],
  }
);

export const JourneyResponseSchema = z.object({
  data: z.object({
    journey: z.object({
      sightings: z.array(z.any()),
      transitions: z.array(z.any()),
      total_events: z.number(),
      span_s: z.number(),
      plate_variants: z.array(z.string()),
    }).optional(),
    correlation: z.object({
      topology_version: z.string(),
      config_version: z.number(),
      trips: z.array(z.any()),
      anomalies: z.array(z.any()),
    }).optional(),
    sightings: z.array(z.any()).optional(),
    transitions: z.array(z.any()).optional(),
    total_events: z.number().optional(),
    span_s: z.number().optional(),
    plate_variants: z.array(z.string()).optional(),
  }),
  meta: z.object({
    truncated: z.boolean(),
    total_matching: z.number(),
    warnings: z.array(z.string()).optional(),
  }),
});

export const ExportQuerySchema = z.object({
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
  time_from: z.string().regex(/^\d{2}:\d{2}$/, 'time_from must be HH:MM').optional(),
  time_to: z.string().regex(/^\d{2}:\d{2}$/, 'time_to must be HH:MM').optional(),
  tz: z.string().optional(),
  q: z.string().optional(),
  purpose: z.string().optional(),
}).strict();
