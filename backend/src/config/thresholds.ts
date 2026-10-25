import fs from 'node:fs';
import path from 'node:path';

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

export function loadThreatThresholds(filePath?: string): ThreatThresholds {
  if (!filePath) return DEFAULT_THRESHOLDS;
  try {
    const resolved = path.resolve(process.cwd(), filePath);
    if (fs.existsSync(resolved)) {
      const content = fs.readFileSync(resolved, 'utf-8');
      const json = JSON.parse(content);
      return {
        low: json.low ?? DEFAULT_THRESHOLDS.low,
        medium: json.medium ?? DEFAULT_THRESHOLDS.medium,
        high: json.high ?? DEFAULT_THRESHOLDS.high,
        critical: json.critical ?? DEFAULT_THRESHOLDS.critical,
      };
    }
  } catch {
    // Fall back to default thresholds
  }
  return DEFAULT_THRESHOLDS;
}
