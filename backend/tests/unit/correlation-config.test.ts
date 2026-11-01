import { describe, it, expect } from 'vitest';
import { CorrelationConfigSchema, loadCorrelationConfig, DEFAULT_CORRELATION_CONFIG } from '../../src/modules/correlation/config.js';

describe('CorrelationConfig schema and loader', () => {
  it('validates default config successfully', () => {
    const parsed = CorrelationConfigSchema.parse(DEFAULT_CORRELATION_CONFIG);
    expect(parsed.version).toBe(1);
    expect(parsed.speed_tolerance).toBe(0.8);
    expect(parsed.max_trajectories).toBe(4);
    expect(parsed.plate_conf.lookalike).toBe(0.7);
  });

  it('rejects invalid config values', () => {
    expect(() =>
      CorrelationConfigSchema.parse({
        ...DEFAULT_CORRELATION_CONFIG,
        speed_tolerance: 1.5, // > 1.0 invalid
      })
    ).toThrow();

    expect(() =>
      CorrelationConfigSchema.parse({
        ...DEFAULT_CORRELATION_CONFIG,
        max_trajectories: 0, // min is 1
      })
    ).toThrow();
  });

  it('loads real configs/correlation.json file', () => {
    const config = loadCorrelationConfig();
    expect(config.version).toBe(1);
    expect(config.merge_gap_s).toBe(120);
    expect(config.trip_break_s).toBe(21600);
  });
});

