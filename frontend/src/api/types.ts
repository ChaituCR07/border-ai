import type { paths } from './schema';

export type CameraResource =
  paths['/api/cameras']['get']['responses'][200]['content']['application/json']['data'][number];

export type AlertResource =
  paths['/api/alerts']['get']['responses'][200]['content']['application/json']['data'][number];

export type EventItem =
  paths['/api/events']['get']['responses'][200]['content']['application/json']['data'][number];

export type EventDetail =
  paths['/api/events/{id}']['get']['responses'][200]['content']['application/json']['data'];

export type ThreatSummary =
  paths['/api/analytics/threats']['get']['responses'][200]['content']['application/json']['data'];

export type CameraActivity =
  paths['/api/analytics/cameras']['get']['responses'][200]['content']['application/json']['data'][number];

export type HealthStatus =
  paths['/api/health']['get']['responses'][200]['content'] extends { 'application/json': infer T }
    ? T
    : { status: string; uptime_s: number; checks: Record<string, string> };
