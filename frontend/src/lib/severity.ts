export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export const SEVERITY_ORDER: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

export interface SeverityMeta {
  label: string;
  icon: string;
  cssVar: string;
  bgVar: string;
  rank: number;
}

export const SEVERITY_META: Record<Severity, SeverityMeta> = {
  CRITICAL: {
    label: 'Critical',
    icon: '▲',
    cssVar: 'var(--sev-critical)',
    bgVar: 'var(--sev-critical-bg)',
    rank: 4,
  },
  HIGH: {
    label: 'High',
    icon: '◆',
    cssVar: 'var(--sev-high)',
    bgVar: 'var(--sev-high-bg)',
    rank: 3,
  },
  MEDIUM: {
    label: 'Medium',
    icon: '●',
    cssVar: 'var(--sev-medium)',
    bgVar: 'var(--sev-medium-bg)',
    rank: 2,
  },
  LOW: {
    label: 'Low',
    icon: '■',
    cssVar: 'var(--sev-low)',
    bgVar: 'var(--sev-low-bg)',
    rank: 1,
  },
};

const DEFAULT_META: SeverityMeta = {
  label: 'Unknown',
  icon: '•',
  cssVar: 'var(--text-dim)',
  bgVar: 'rgba(100, 116, 139, 0.15)',
  rank: 0,
};

export function getSeverityMeta(severity?: string | null): SeverityMeta {
  if (!severity) return DEFAULT_META;
  const upper = severity.toUpperCase() as Severity;
  return SEVERITY_META[upper] ?? DEFAULT_META;
}

export function compareSeverityDesc(a: string, b: string): number {
  const rankA = getSeverityMeta(a).rank;
  const rankB = getSeverityMeta(b).rank;
  return rankB - rankA;
}
