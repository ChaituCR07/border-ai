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

export interface AnalyticsRepo {
  getEventTimeseries(
    from: string,
    to: string,
    bucket: 'hour' | 'day',
    cameraId?: string
  ): Promise<{ buckets: EventTimeSeriesBucket[]; by_type: EventTypeCount[] }>;

  getCameraStats(from?: string, to?: string): Promise<CameraActivityStats[]>;

  getThreatStats(from: string, to: string, cameraId?: string): Promise<ThreatSummaryStats>;
}
