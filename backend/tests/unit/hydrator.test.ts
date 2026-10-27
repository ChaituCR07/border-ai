import { describe, it, expect, vi } from 'vitest';
import { parseAlertEnvelope } from '../../src/realtime/envelope.js';
import { AlertHydrator } from '../../src/realtime/hydrator.js';
import type { AlertsRepo } from '../../src/modules/alerts/repo.js';

describe('Envelope Parser & AlertHydrator Unit Tests', () => {
  const sampleFields = {
    v: '1',
    event_id: '11111111-1111-1111-1111-111111111111',
    type: 'THREAT_ALERT',
    camera: 'CAM-03',
    ts: '1700000000000',
    severity: 'CRITICAL',
    run_id: 'run-1',
    data: JSON.stringify({
      event_id: '11111111-1111-1111-1111-111111111111',
      type: 'THREAT_ALERT',
      camera_id: 'CAM-03',
      timestamp: '2026-10-27T12:00:00.000000Z',
      details: {
        alert_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        priority: 'CRITICAL',
        threat_score: 92,
        plate: 'KA01AB1234',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        snapshot_path: 'CAM-03/snap.jpg',
      },
    }),
  };

  it('parses a valid Redis stream entry into an AlertEnvelope', () => {
    const env = parseAlertEnvelope(sampleFields);
    expect(env).not.toBeNull();
    expect(env?.alert_id).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
    expect(env?.event_id).toBe('11111111-1111-1111-1111-111111111111');
    expect(env?.camera_id).toBe('CAM-03');
    expect(env?.priority).toBe('CRITICAL');
    expect(env?.threat_score).toBe(92);
    expect(env?.plate).toBe('KA01AB1234');
    expect(env?.snapshot_url).toBe('/api/snapshots/CAM-03/snap.jpg');
    expect(env?.snapshot_available).toBe(true);
  });

  it('returns null when envelope version is not 1 or fields are malformed', () => {
    expect(parseAlertEnvelope({ ...sampleFields, v: '2' })).toBeNull();
    expect(parseAlertEnvelope({ ...sampleFields, data: 'not-json' })).toBeNull();
    expect(parseAlertEnvelope({ ...sampleFields, data: JSON.stringify({}) })).toBeNull();
  });

  it('hydrates from database immediately when row exists (persisted: true)', async () => {
    const mockRepo: AlertsRepo = {
      list: vi.fn(),
      getById: vi.fn().mockResolvedValue({
        alert_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        event_id: '11111111-1111-1111-1111-111111111111',
        priority: 'CRITICAL',
        status: 'OPEN',
        acknowledged_by: null,
        acknowledged_at: null,
        created_at: '2026-10-27T12:00:00.000000Z',
        event: {
          camera_id: 'CAM-03',
          event_type: 'RESTRICTED_ZONE_ENTRY',
          threat_score: 92,
          plate: 'KA01AB1234',
          snapshot_url: '/api/snapshots/CAM-03/snap.jpg',
        },
      }),
      acknowledge: vi.fn(),
    };

    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const hydrator = new AlertHydrator(mockRepo, sleepFn);
    const env = parseAlertEnvelope(sampleFields)!;

    const alertView = await hydrator.hydrate(env);

    expect(alertView.persisted).toBe(true);
    expect(mockRepo.getById).toHaveBeenCalledTimes(1);
    expect(sleepFn).not.toHaveBeenCalled();
  });

  it('retries according to schedule and succeeds when DB row appears (persisted: true)', async () => {
    let callCount = 0;
    const mockRepo: AlertsRepo = {
      list: vi.fn(),
      getById: vi.fn().mockImplementation(async () => {
        callCount += 1;
        if (callCount < 3) return null; // Sink still processing
        return {
          alert_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
          event_id: '11111111-1111-1111-1111-111111111111',
          priority: 'CRITICAL',
          status: 'OPEN',
          acknowledged_by: null,
          acknowledged_at: null,
          created_at: '2026-10-27T12:00:00.000000Z',
          event: {
            camera_id: 'CAM-03',
            event_type: 'RESTRICTED_ZONE_ENTRY',
            threat_score: 92,
            plate: 'KA01AB1234',
            snapshot_url: '/api/snapshots/CAM-03/snap.jpg',
          },
        };
      }),
      acknowledge: vi.fn(),
    };

    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const hydrator = new AlertHydrator(mockRepo, sleepFn);
    const env = parseAlertEnvelope(sampleFields)!;

    const alertView = await hydrator.hydrate(env);

    expect(alertView.persisted).toBe(true);
    expect(callCount).toBe(3);
    expect(sleepFn).toHaveBeenCalledTimes(2); // Retried after 50ms, 100ms
  });

  it('falls back to envelope data with persisted: false when database row never appears', async () => {
    const mockRepo: AlertsRepo = {
      list: vi.fn(),
      getById: vi.fn().mockResolvedValue(null),
      acknowledge: vi.fn(),
    };

    const sleepFn = vi.fn().mockResolvedValue(undefined);
    const hydrator = new AlertHydrator(mockRepo, sleepFn);
    const env = parseAlertEnvelope(sampleFields)!;

    const alertView = await hydrator.hydrate(env);

    expect(alertView.persisted).toBe(false);
    expect(alertView.alert_id).toBe(env.alert_id);
    expect(alertView.status).toBe('OPEN');
    expect(alertView.event.threat_score).toBe(92);
  });

  it('suppresses duplicate alert broadcasts within the time window', () => {
    const hydrator = new AlertHydrator({} as any);

    expect(hydrator.isDuplicate('alert-1')).toBe(false);
    expect(hydrator.isDuplicate('alert-1')).toBe(true);
    expect(hydrator.isDuplicate('alert-2')).toBe(false);
  });
});
