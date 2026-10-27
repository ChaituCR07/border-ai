import { describe, it, expect } from 'vitest';
import { applyAlertMessage, type AlertMessage } from './applyAlertMessage';
import type { AlertView } from '@border-ai/protocol';

function makeAlert(alert_id: string, status: AlertView['status'] = 'OPEN', score = 80): AlertView {
  return {
    alert_id,
    event_id: `evt-${alert_id}`,
    priority: 'CRITICAL',
    status,
    acknowledged_by: status === 'ACKNOWLEDGED' ? 'user-1' : null,
    acknowledged_at: status === 'ACKNOWLEDGED' ? new Date().toISOString() : null,
    created_at: new Date().toISOString(),
    persisted: true,
    event: {
      camera_id: 'CAM-01',
      event_type: 'ZONE_ENTRY',
      threat_score: score,
      plate: null,
      timestamp: new Date().toISOString(),
      snapshot_url: null,
      snapshot_available: false,
    },
  };
}

describe('Idempotent Alert Message Reducer (applyAlertMessage)', () => {
  it('inserts newly created open alert into the list', () => {
    const initial: AlertView[] = [makeAlert('a1')];
    const msg: AlertMessage = {
      v: 1,
      type: 'alert.created',
      seq: 10,
      data: { alert: makeAlert('a2') },
    };

    const next = applyAlertMessage(initial, msg);
    expect(next).toHaveLength(2);
    expect(next.map((a) => a.alert_id)).toEqual(['a2', 'a1']);
  });

  it('is completely idempotent when receiving the same created message twice', () => {
    const initial: AlertView[] = [makeAlert('a1')];
    const msg: AlertMessage = {
      v: 1,
      type: 'alert.created',
      seq: 10,
      data: { alert: makeAlert('a2') },
    };

    const pass1 = applyAlertMessage(initial, msg);
    const pass2 = applyAlertMessage(pass1, msg);
    expect(pass2).toHaveLength(2);
    expect(pass2).toEqual(pass1);
  });

  it('removes alert from list when status is updated to ACKNOWLEDGED', () => {
    const initial: AlertView[] = [makeAlert('a1'), makeAlert('a2')];
    const msg: AlertMessage = {
      v: 1,
      type: 'alert.updated',
      seq: 11,
      data: { alert: makeAlert('a1', 'ACKNOWLEDGED') },
    };

    const next = applyAlertMessage(initial, msg);
    expect(next).toHaveLength(1);
    expect(next[0]!.alert_id).toBe('a2');
  });

  it('is a safe no-op when receiving an update for an unknown alert', () => {
    const initial: AlertView[] = [makeAlert('a1')];
    const msg: AlertMessage = {
      v: 1,
      type: 'alert.updated',
      seq: 12,
      data: { alert: makeAlert('a999', 'ACKNOWLEDGED') },
    };

    const next = applyAlertMessage(initial, msg);
    expect(next).toHaveLength(1);
    expect(next[0]!.alert_id).toBe('a1');
  });

  it('updates alert fields when an open alert is updated with new data', () => {
    const initial: AlertView[] = [makeAlert('a1', 'OPEN', 60)];
    const msg: AlertMessage = {
      v: 1,
      type: 'alert.updated',
      seq: 13,
      data: { alert: makeAlert('a1', 'OPEN', 95) },
    };

    const next = applyAlertMessage(initial, msg);
    expect(next).toHaveLength(1);
    expect(next[0]!.event.threat_score).toBe(95);
  });
});
