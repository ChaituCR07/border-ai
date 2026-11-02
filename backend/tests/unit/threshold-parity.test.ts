import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  loadThreatThresholdConfig,
  tierForScore,
  ThreatThresholdConfigSchema,
} from '../../src/config/thresholds.js';

describe('Threat Threshold Parity & Fixture Verification', () => {
  it('validates configs/threat_thresholds.json against schema', () => {
    const config = loadThreatThresholdConfig();
    expect(config.version).toBe(1);
    expect(config.tiers).toHaveLength(4);
    expect(config.tiers.map(t => t.name)).toEqual(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
  });

  it('matches all fixture boundary cases in docs/fixtures/threshold_cases.json', () => {
    const fixturePath = path.resolve(process.cwd(), '../docs/fixtures/threshold_cases.json');
    const content = fs.existsSync(fixturePath)
      ? fs.readFileSync(fixturePath, 'utf-8')
      : fs.readFileSync(path.resolve(process.cwd(), 'docs/fixtures/threshold_cases.json'), 'utf-8');

    const cases: Array<{ score: number; tier: string }> = JSON.parse(content);
    expect(cases.length).toBeGreaterThanOrEqual(8);

    const config = loadThreatThresholdConfig();
    for (const tc of cases) {
      const derived = tierForScore(tc.score, config);
      expect(derived).toBe(tc.tier);
    }
  });

  it('handles custom threshold overrides correctly', () => {
    const customConfig = ThreatThresholdConfigSchema.parse({
      version: 1,
      tiers: [
        { name: 'LOW', min: 0 },
        { name: 'MEDIUM', min: 40 },
        { name: 'HIGH', min: 70 },
        { name: 'CRITICAL', min: 90 },
      ],
    });

    expect(tierForScore(39, customConfig)).toBe('LOW');
    expect(tierForScore(40, customConfig)).toBe('MEDIUM');
    expect(tierForScore(69, customConfig)).toBe('MEDIUM');
    expect(tierForScore(70, customConfig)).toBe('HIGH');
    expect(tierForScore(89, customConfig)).toBe('HIGH');
    expect(tierForScore(90, customConfig)).toBe('CRITICAL');
  });
});
