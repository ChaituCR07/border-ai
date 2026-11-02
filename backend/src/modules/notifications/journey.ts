import { type TopologyIndex } from '../correlation/topology.js';
import { type CorrelationConfig } from '../correlation/config.js';
import { correlate } from '../correlation/correlate.js';
import { type Sighting } from '../investigation/journey.js';

export interface JourneySummaryResult {
  text: string;
  warnings: string[];
}

export interface JourneyDeps {
  getSightings: (plate: string, fromIso: string, toIso: string) => Promise<Sighting[]>;
  topo: TopologyIndex;
  config: CorrelationConfig;
  timeoutMs?: number;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const mm = String(d.getUTCMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  } catch {
    return iso;
  }
}

export async function buildJourneySummary(
  plate: string | null | undefined,
  alertCameraId: string,
  alertTimeIso: string,
  deps: JourneyDeps
): Promise<JourneySummaryResult | null> {
  if (!plate) {
    return null;
  }

  const timeoutMs = deps.timeoutMs ?? 2000;

  const promise = (async () => {
    const alertMs = new Date(alertTimeIso).getTime();
    const fromIso = new Date(alertMs - 7200 * 1000).toISOString(); // 2 hours prior
    const toIso = alertTimeIso;

    const sightings = await deps.getSightings(plate, fromIso, toIso);
    if (!sightings || sightings.length === 0) {
      return null;
    }

    const correlation = correlate(sightings, deps.topo, deps.config);
    if (correlation.trips.length === 0) {
      return null;
    }

    // Select the most recent trip
    const latestTrip = correlation.trips[correlation.trips.length - 1]!;
    if (latestTrip.trajectories.length === 0) {
      return null;
    }

    // Pick trajectory with highest confidence
    const sortedTrajs = [...latestTrip.trajectories].sort(
      (a, b) => b.summary.mean_confidence - a.summary.mean_confidence
    );
    const bestTraj = sortedTrajs[0]!;

    if (bestTraj.sightings.length === 0) {
      return null;
    }

    const segments = bestTraj.sightings.map(s => {
      const timeStr = formatTime(s.first_seen);
      const isCurrent = s.camera_id === alertCameraId;
      return `${s.camera_id} ${timeStr}${isCurrent ? ' (this alert)' : ''}`;
    });

    const journeyText = segments.join(' → ');

    // Collect anomaly warnings
    const warnings: string[] = [];
    for (const anom of correlation.anomalies) {
      if (anom.type === 'IMPOSSIBLE_TRAVEL') {
        warnings.push('Possible duplicate plate or misread: seen at locations that cannot be reached in the elapsed time.');
      } else if (anom.type === 'MISSED_CAMERA') {
        warnings.push(`Expected intermediate camera detection missed: ${anom.details.missed_cameras?.join(', ') || 'route checkpoint'}.`);
      } else if (anom.type === 'MULTIPLE_TRAJECTORIES') {
        warnings.push('Simultaneous or diverging trajectories detected for this license plate.');
      }
    }

    return {
      text: journeyText,
      warnings,
    };
  })();

  try {
    const timeout = new Promise<null>(resolve => setTimeout(() => resolve(null), timeoutMs));
    return await Promise.race([promise, timeout]);
  } catch (err) {
    console.debug('[journey] Best-effort journey summary error:', err);
    return null;
  }
}
