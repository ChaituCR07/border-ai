import { AppError } from '../../common/errors.js';
import { plateNorm } from '../../common/plate.js';

export const KNOWN_EVENT_TYPES = [
  'RESTRICTED_ZONE_ENTRY',
  'ZONE_INTRUSION',
  'TRIPWIRE_CROSSING',
  'DIRECTION_VIOLATION',
  'LOITERING_DETECTED',
  'SPEED_ANOMALY',
  'ANPR_DETECTION',
  'WATCHLIST_HIT',
  'PERSON_DETECTED',
  'VEHICLE_DETECTED',
  'THREAT_ALERT',
] as const;

export interface OmniboxClassification {
  eventId?: string;
  cameraId?: string;
  plate?: string;
  plateMatch?: 'lookalike';
  eventType?: string;
}

const UUID_REGEX = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
const CAMERA_REGEX = /^CAM[-_ ]?0*(\d+)$/i;

export function classifyOmniboxQuery(raw: string): OmniboxClassification {
  const trimmed = raw.trim();
  if (!trimmed) return {};

  // 1. Event ID UUID
  if (UUID_REGEX.test(trimmed)) {
    return { eventId: trimmed.toLowerCase() };
  }

  // 2. Camera ID (e.g. CAM-03, CAM03, cam_3)
  const camMatch = trimmed.match(CAMERA_REGEX);
  if (camMatch && camMatch[1]) {
    const num = camMatch[1].padStart(2, '0');
    return { cameraId: `CAM-${num}` };
  }

  // 3. Known Event Type token (exact or partial keyword)
  const upper = trimmed.toUpperCase().replace(/[\s-]+/g, '_');
  const directTypeMatch = KNOWN_EVENT_TYPES.find(
    (t) => t === upper || t.includes(upper) || upper.includes(t)
  );
  if (directTypeMatch) {
    return { eventType: directTypeMatch };
  }

  // 4. Plate number (contains both digit and letter, 4-16 alphanumeric chars)
  const norm = plateNorm(trimmed);
  const hasLetter = /[A-Z]/.test(norm);
  const hasDigit = /[0-9]/.test(norm);

  if (hasLetter && hasDigit && norm.length >= 4 && norm.length <= 16) {
    return {
      plate: norm,
      plateMatch: 'lookalike',
    };
  }

  throw new AppError(
    400,
    'VALIDATION_ERROR',
    `Could not interpret '${trimmed}'; try 'plate:KA01AB1234', 'cam:CAM-03', or an event type like 'restricted'`
  );
}
