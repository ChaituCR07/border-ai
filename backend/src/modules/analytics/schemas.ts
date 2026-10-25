import { z } from 'zod';

export const AnalyticsTimeQuerySchema = z.object({
  bucket: z.enum(['hour', 'day']).default('hour'),
  camera_id: z.string().optional(),
  from: z.string().datetime({ offset: true }).optional(),
  to: z.string().datetime({ offset: true }).optional(),
}).strict();

export const AnalyticsEventsSchema = z.object({
  bucket_tz: z.literal('UTC'),
  buckets: z.array(z.object({
    bucket: z.string(),
    total: z.number(),
    critical: z.number(),
    high: z.number(),
    medium: z.number(),
    low: z.number(),
  })),
  by_type: z.array(z.object({
    event_type: z.string(),
    count: z.number(),
  })),
});

export const AnalyticsCamerasSchema = z.object({
  data: z.array(z.object({
    camera_id: z.string(),
    events: z.number(),
    alerts_open: z.number(),
    max_threat_score: z.number(),
    last_event_at: z.string().nullable(),
  })),
});

export const AnalyticsThreatsSchema = z.object({
  data: z.object({
    severity_counts: z.record(z.number()),
    open_alerts_by_priority: z.record(z.number()),
    score_histogram: z.array(z.object({
      from: z.number(),
      to: z.number(),
      count: z.number(),
    })),
    top_event_types: z.array(z.object({
      event_type: z.string(),
      count: z.number(),
    })),
    top_plates: z.array(z.object({
      plate: z.string(),
      events: z.number(),
      max_score: z.number(),
    })),
  }),
});
