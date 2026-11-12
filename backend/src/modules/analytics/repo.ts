export interface EventTimeSeriesBucket {
  bucket: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface EventTypeCount {
  event_type: string;
  count: number;
}

export interface CameraActivityStats {
  camera_id: string;
  events: number;
  alerts_open: number;
  max_threat_score: number;
  last_event_at: string | null;
}

export interface ThreatSummaryStats {
  severity_counts: Record<string, number>;
  open_alerts_by_priority: Record<string, number>;
  score_histogram: { from: number; to: number; count: number }[];
  top_event_types: { event_type: string; count: number }[];
  top_plates: { plate: string; events: number; max_score: number }[];
}

export interface ResolutionBreakdown {
  resolution: string;
  count: number;
}

export interface ResolutionAnalytics {
  total_resolved: number;
  false_positive_count: number;
  false_positive_rate: number;
  by_resolution: ResolutionBreakdown[];
  by_camera: { camera_id: string; total: number; false_positives: number }[];
  by_rule: { rule_type: string; total: number; false_positives: number }[];
  by_tier: { tier: string; total: number; false_positives: number }[];
}

export interface AnalyticsRepo {
  getEventTimeseries(
    from: string,
    to: string,
    bucket: 'hour' | 'day',
    cameraId?: string
  ): Promise<{ buckets: EventTimeSeriesBucket[]; by_type: EventTypeCount[] }>;

  getCameraStats(from?: string, to?: string): Promise<CameraActivityStats[]>;

  getThreatStats(from: string, to: string, cameraId?: string): Promise<ThreatSummaryStats>;

  getResolutionStats(from?: string, to?: string): Promise<ResolutionAnalytics>;
}
