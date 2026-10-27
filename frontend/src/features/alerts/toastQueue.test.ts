import { describe, it, expect } from 'vitest';
import { enqueue, dismissById, expire, visible, type Toast } from './toastQueue';
import type { AlertView } from '@border-ai/protocol';

function makeAlert(overrides: {
  alert_id?: string;
  event_id?: string;
  priority?: AlertView['priority'];
  status?: AlertView['status'];
  event?: {
    camera_id?: string;
    event_type?: string;
    threat_score?: number;
    plate?: string | null;
    timestamp?: string;
    snapshot_url?: string | null;
    snapshot_available?: boolean;
  };
}): AlertView {
  return {
    alert_id: overrides.alert_id ?? 'alert-1',
    event_id: overrides.event_id ?? 'evt-1',
    priority: overrides.priority ?? 'CRITICAL',
    status: overrides.status ?? 'OPEN',
    acknowledged_by: null,
    acknowledged_at: null,
    created_at: new Date().toISOString(),
    persisted: true,
    event: {
      camera_id: overrides.event?.camera_id ?? 'CAM-01',
      event_type: overrides.event?.event_type ?? 'PERSON_DETECTED',
      threat_score: overrides.event?.threat_score ?? 85,
      plate: overrides.event?.plate ?? null,
      timestamp: overrides.event?.timestamp ?? new Date().toISOString(),
      snapshot_url: overrides.event?.snapshot_url ?? null,
      snapshot_available: overrides.event?.snapshot_available ?? false,
    },
  };
}

describe('Toast Queue Policy (ADR 0021)', () => {
  it('never produces toasts for MEDIUM or LOW priority alerts', () => {
    let queue: Toast[] = [];
    const now = 1000;

    queue = enqueue(queue, makeAlert({ priority: 'MEDIUM' }), now);
    expect(queue).toHaveLength(0);

    queue = enqueue(queue, makeAlert({ priority: 'LOW' }), now);
    expect(queue).toHaveLength(0);
  });

  it('marks CRITICAL toasts as sticky and HIGH toasts with 15s expiration', () => {
    let queue: Toast[] = [];
    const now = 10_000;

    const critical = makeAlert({ alert_id: 'c1', priority: 'CRITICAL' });
    const high = makeAlert({ alert_id: 'h1', priority: 'HIGH', event: { camera_id: 'CAM-02' } });

    queue = enqueue(queue, critical, now);
    queue = enqueue(queue, high, now);

    const cToast = queue.find(t => t.id === 'c1');
    const hToast = queue.find(t => t.id === 'h1');

    expect(cToast?.expiresAt).toBeNull();
    expect(hToast?.expiresAt).toBe(now + 15_000);
  });

  it('coalesces bursts with same camera and plate within 20s, keeping highest score', () => {
    let queue: Toast[] = [];
    const t0 = 1000;

    const a1 = makeAlert({
      alert_id: 'a1',
      priority: 'HIGH',
      event: { camera_id: 'CAM-03', plate: 'KA01AB1234', threat_score: 75 },
    });
    const a2 = makeAlert({
      alert_id: 'a2',
      priority: 'CRITICAL',
      event: { camera_id: 'CAM-03', plate: 'KA01AB1234', threat_score: 95 },
    });

    queue = enqueue(queue, a1, t0);
    expect(queue).toHaveLength(1);
    expect(queue[0]!.count).toBe(1);
    expect(queue[0]!.alert.event.threat_score).toBe(75);

    // Within 20s window (e.g. at t0 + 5s)
    queue = enqueue(queue, a2, t0 + 5000);
    expect(queue).toHaveLength(1);
    expect(queue[0]!.count).toBe(2);
    expect(queue[0]!.id).toBe('a2'); // higher threat alert becomes representative
    expect(queue[0]!.alert.event.threat_score).toBe(95);
    expect(queue[0]!.expiresAt).toBeNull(); // upgraded to sticky because a2 is CRITICAL
  });

  it('does not coalesce if camera or plate differs', () => {
    let queue: Toast[] = [];
    const now = 1000;

    const a1 = makeAlert({
      alert_id: 'a1',
      priority: 'HIGH',
      event: { camera_id: 'CAM-03', plate: 'KA01AB1234' },
    });
    const a2 = makeAlert({
      alert_id: 'a2',
      priority: 'HIGH',
      event: { camera_id: 'CAM-03', plate: 'KA02CD5678' },
    });

    queue = enqueue(queue, a1, now);
    queue = enqueue(queue, a2, now);
    expect(queue).toHaveLength(2);
  });

  it('does not coalesce if burst window has expired (> 20s)', () => {
    let queue: Toast[] = [];
    const t0 = 1000;

    const a1 = makeAlert({
      alert_id: 'a1',
      priority: 'HIGH',
      event: { camera_id: 'CAM-03', plate: 'KA01AB1234' },
    });
    const a2 = makeAlert({
      alert_id: 'a2',
      priority: 'HIGH',
      event: { camera_id: 'CAM-03', plate: 'KA01AB1234' },
    });

    queue = enqueue(queue, a1, t0);
    queue = enqueue(queue, a2, t0 + 21_000); // 21s later
    expect(queue).toHaveLength(2);
  });

  it('caps visible toasts at 3 and counts hidden toasts', () => {
    let queue: Toast[] = [];
    const now = 1000;

    for (let i = 1; i <= 5; i++) {
      queue = enqueue(
        queue,
        makeAlert({
          alert_id: `alert-${i}`,
          priority: i % 2 === 0 ? 'CRITICAL' : 'HIGH',
          event: { camera_id: `CAM-0${i}`, threat_score: 60 + i },
        }),
        now + i
      );
    }

    const { shown, hidden } = visible(queue);
    expect(shown).toHaveLength(3);
    expect(hidden).toBe(2);
    // CRITICAL toasts are sorted above HIGH
    expect(shown[0]!.alert.priority).toBe('CRITICAL');
  });

  it('expires only expired HIGH toasts while leaving sticky CRITICAL toasts', () => {
    let queue: Toast[] = [];
    const t0 = 10_000;

    queue = enqueue(queue, makeAlert({ alert_id: 'c1', priority: 'CRITICAL', event: { camera_id: 'CAM-1' } }), t0);
    queue = enqueue(queue, makeAlert({ alert_id: 'h1', priority: 'HIGH', event: { camera_id: 'CAM-2' } }), t0);

    // At t0 + 10s: neither expired
    queue = expire(queue, t0 + 10_000);
    expect(queue).toHaveLength(2);

    // At t0 + 16s: HIGH expired (15s lifetime), CRITICAL remains
    queue = expire(queue, t0 + 16_000);
    expect(queue).toHaveLength(1);
    expect(queue[0]!.id).toBe('c1');
  });

  it('dismissById removes specific toast', () => {
    let queue: Toast[] = [];
    const now = 1000;

    queue = enqueue(queue, makeAlert({ alert_id: 'a1', priority: 'CRITICAL', event: { camera_id: 'CAM-1' } }), now);
    queue = enqueue(queue, makeAlert({ alert_id: 'a2', priority: 'HIGH', event: { camera_id: 'CAM-2' } }), now);

    queue = dismissById(queue, 'a1');
    expect(queue).toHaveLength(1);
    expect(queue[0]!.id).toBe('a2');
  });
});
