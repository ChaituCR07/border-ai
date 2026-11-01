import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod';

export const CorrelationConfigSchema = z.object({
  version: z.number().int().min(1),
  merge_gap_s: z.number().positive().default(120),
  trip_break_s: z.number().positive().default(21600),
  speed_tolerance: z.number().positive().max(1.0).default(0.8),
  overlap_tolerance_s: z.number().nonnegative().default(5),
  max_trajectories: z.number().int().min(1).max(20).default(4),
  min_link_confidence: z.number().min(0).max(1).default(0.3),
  plate_conf: z.object({
    exact: z.number().min(0).max(1).default(1.0),
    lookalike: z.number().min(0).max(1).default(0.7),
    unknown: z.number().min(0).max(1).default(1.0),
  }),
  timing_conf: z.object({
    typical: z.number().min(0).max(1).default(1.0),
    in_range: z.number().min(0).max(1).default(0.7),
    fast: z.number().min(0).max(1).default(0.5),
    slow_near: z.number().min(0).max(1).default(0.6),
    slow_far: z.number().min(0).max(1).default(0.4),
    unlinked: z.number().min(0).max(1).default(0.4),
  }),
  appearance: z.object({
    enabled: z.boolean().default(false),
  }).default({ enabled: false }),
});

export type CorrelationConfig = z.infer<typeof CorrelationConfigSchema>;

export const DEFAULT_CORRELATION_CONFIG: CorrelationConfig = {
  version: 1,
  merge_gap_s: 120,
  trip_break_s: 21600,
  speed_tolerance: 0.8,
  overlap_tolerance_s: 5,
  max_trajectories: 4,
  min_link_confidence: 0.3,
  plate_conf: {
    exact: 1.0,
    lookalike: 0.7,
    unknown: 1.0,
  },
  timing_conf: {
    typical: 1.0,
    in_range: 0.7,
    fast: 0.5,
    slow_near: 0.6,
    slow_far: 0.4,
    unlinked: 0.4,
  },
  appearance: {
    enabled: false,
  },
};

export function loadCorrelationConfig(filePath?: string): CorrelationConfig {
  const targetPath = filePath || path.resolve(process.cwd(), 'configs/correlation.json');
  try {
    if (fs.existsSync(targetPath)) {
      const raw = fs.readFileSync(targetPath, 'utf-8');
      const parsed = JSON.parse(raw);
      return CorrelationConfigSchema.parse(parsed);
    }
  } catch (err: any) {
    throw new Error(`Failed to load or validate correlation config from ${targetPath}: ${err.message}`);
  }
  return DEFAULT_CORRELATION_CONFIG;
}
