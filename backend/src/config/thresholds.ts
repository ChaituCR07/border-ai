import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod';

export const ThreatTierSchema = z.object({
  name: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  min: z.number().int().min(0).max(100),
});

export const ThreatThresholdConfigSchema = z.object({
  version: z.number().int().min(1),
  tiers: z.array(ThreatTierSchema).min(1),
});

export type ThreatThresholdConfig = z.infer<typeof ThreatThresholdConfigSchema>;
export type ThreatTierName = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ThreatThresholds {
  low: { min: number; max: number };
  medium: { min: number; max: number };
  high: { min: number; max: number };
  critical: { min: number; max: number };
}

export const DEFAULT_THRESHOLDS: ThreatThresholds = {
  low: { min: 0, max: 29 },
  medium: { min: 30, max: 59 },
  high: { min: 60, max: 79 },
  critical: { min: 80, max: 100 },
};

export const DEFAULT_TIERS_CONFIG: ThreatThresholdConfig = {
  version: 1,
  tiers: [
    { name: 'LOW', min: 0 },
    { name: 'MEDIUM', min: 30 },
    { name: 'HIGH', min: 60 },
    { name: 'CRITICAL', min: 80 },
  ],
};

export function loadThreatThresholdConfig(filePath?: string): ThreatThresholdConfig {
  const candidatePaths = [
    filePath,
    path.resolve(process.cwd(), 'configs/threat_thresholds.json'),
    path.resolve(process.cwd(), '../configs/threat_thresholds.json'),
  ].filter(Boolean) as string[];

  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      try {
        const raw = fs.readFileSync(p, 'utf-8');
        const parsed = JSON.parse(raw);
        return ThreatThresholdConfigSchema.parse(parsed);
      } catch (err) {
        console.warn(`[thresholds] Failed parsing ${p}:`, err);
      }
    }
  }
  return DEFAULT_TIERS_CONFIG;
}

export function tierForScore(score: number, config?: ThreatThresholdConfig): ThreatTierName {
  const cfg = config || loadThreatThresholdConfig();
  const sorted = [...cfg.tiers].sort((a, b) => a.min - b.min);
  let matched: ThreatTierName = sorted[0]?.name ?? 'LOW';
  for (const tier of sorted) {
    if (score >= tier.min) {
      matched = tier.name;
    }
  }
  return matched;
}

export function loadThreatThresholds(filePath?: string): ThreatThresholds {
  const config = loadThreatThresholdConfig(filePath);
  const findTier = (name: ThreatTierName) => config.tiers.find(t => t.name === name);
  const lowMin = findTier('LOW')?.min ?? 0;
  const medMin = findTier('MEDIUM')?.min ?? 30;
  const highMin = findTier('HIGH')?.min ?? 60;
  const critMin = findTier('CRITICAL')?.min ?? 80;

  return {
    low: { min: lowMin, max: medMin - 1 },
    medium: { min: medMin, max: highMin - 1 },
    high: { min: highMin, max: critMin - 1 },
    critical: { min: critMin, max: 100 },
  };
}
