import type { Severity } from '@border-ai/protocol';

export interface AlertEnvelope {
  alert_id: string;
  event_id: string;
  camera_id: string;
  event_type: string;
  priority: Severity;
  threat_score: number;
  plate: string | null;
  timestamp: string;
  snapshot_url: string | null;
  snapshot_available: boolean;
}

export function parseAlertEnvelope(fields: Record<string, string>): AlertEnvelope | null {
  if (fields.v !== '1') return null;

  try {
    const rawData = fields.data;
    if (!rawData) return null;

    const data = JSON.parse(rawData);
    const details = data.details || {};

    const alertId = String(details.alert_id || data.alert_id || fields.alert_id || '').trim();
    const eventId = String(data.event_id || fields.event_id || '').trim();
    const cameraId = String(data.camera_id || data.camera || fields.camera || '').trim();

    if (!alertId || !eventId || !cameraId) {
      return null;
    }

    const rawPriority = String(details.priority || details.level || fields.severity || data.severity || 'LOW').toUpperCase();
    const priority: Severity = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].includes(rawPriority)
      ? (rawPriority as Severity)
      : 'LOW';

    const threatScore = Number(details.threat_score ?? data.threat_score ?? 0);
    const eventType = String(details.event_type || data.type || fields.type || 'THREAT_ALERT');
    const plate = details.plate || data.plate || null;

    // Timestamp
    let timestamp = data.timestamp || new Date(Number(fields.ts) || Date.now()).toISOString();
    try {
      timestamp = new Date(timestamp).toISOString();
    } catch {
      timestamp = new Date().toISOString();
    }

    const snapshotPath = details.snapshot_path || data.snapshot_path || null;
    const snapshotUrl = snapshotPath ? `/api/snapshots/${snapshotPath}` : null;

    return {
      alert_id: alertId,
      event_id: eventId,
      camera_id: cameraId,
      event_type: eventType,
      priority,
      threat_score: Math.min(100, Math.max(0, threatScore)),
      plate: plate ? String(plate) : null,
      timestamp,
      snapshot_url: snapshotUrl,
      snapshot_available: Boolean(snapshotUrl),
    };
  } catch {
    return null;
  }
}
