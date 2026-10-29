import { describe, it, expect } from 'vitest';
import { buildJourney, isoToMicros, type EventLite } from '../../src/modules/investigation/journey.js';

describe('Journey builder (pure function)', () => {
  it('correctly builds journey for plan acceptance example (CAM-03 -> CAM-04 -> CAM-05 with +28s and +72s gaps)', () => {
    const events: EventLite[] = [
      {
        event_id: 'e1',
        camera_id: 'CAM-03',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:00:00.000000Z',
        threat_score: 50,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'e2',
        camera_id: 'CAM-03',
        event_type: 'ANPR_MATCH',
        timestamp: '2026-10-25T10:00:10.000000Z',
        threat_score: 75,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'e3',
        camera_id: 'CAM-04',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:00:38.000000Z',
        threat_score: 60,
        plate: 'KA0IAB1234', // lookalike variant
      },
      {
        event_id: 'e4',
        camera_id: 'CAM-05',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        timestamp: '2026-10-25T10:01:50.000000Z',
        threat_score: 90,
        plate: 'KA01AB1234',
      },
    ];

    const journey = buildJourney(events);

    expect(journey.total_events).toBe(4);
    expect(journey.sightings).toHaveLength(3);
    expect(journey.sightings.map(s => s.camera_id)).toEqual(['CAM-03', 'CAM-04', 'CAM-05']);

    // Sighting 1 (CAM-03, 2 merged events)
    expect(journey.sightings[0]?.camera_id).toBe('CAM-03');
    expect(journey.sightings[0]?.first_seen).toBe('2026-10-25T10:00:00.000000Z');
    expect(journey.sightings[0]?.last_seen).toBe('2026-10-25T10:00:10.000000Z');
    expect(journey.sightings[0]?.event_count).toBe(2);
    expect(journey.sightings[0]?.max_score).toBe(75);

    // Transitions
    expect(journey.transitions).toHaveLength(2);
    expect(journey.transitions[0]).toEqual({
      from: 'CAM-03',
      to: 'CAM-04',
      gap_s: 28, // 10:00:38 - 10:00:10 = 28s
    });
    expect(journey.transitions[1]).toEqual({
      from: 'CAM-04',
      to: 'CAM-05',
      gap_s: 72, // 10:01:50 - 10:00:38 = 72s
    });

    // Plate variants aggregated
    expect(journey.plate_variants).toEqual(['KA01AB1234', 'KA0IAB1234']);
    expect(journey.span_s).toBe(110); // 10:01:50 - 10:00:00 = 110s
  });

  it('collapses 40 events in 30s on one camera into 1 sighting with event_count 40', () => {
    const baseTime = new Date('2026-10-25T12:00:00.000Z').getTime();
    const events: EventLite[] = Array.from({ length: 40 }, (_, i) => {
      const ms = baseTime + Math.floor((i * 30000) / 40);
      return {
        event_id: `ev-${i.toString().padStart(3, '0')}`,
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        timestamp: new Date(ms).toISOString(),
        threat_score: 50 + (i % 20),
        plate: 'MH12AB1234',
      };
    });

    const journey = buildJourney(events);
    expect(journey.sightings).toHaveLength(1);
    expect(journey.sightings[0]?.event_count).toBe(40);
    expect(journey.sightings[0]?.event_ids).toHaveLength(40);
    expect(journey.transitions).toHaveLength(0);
  });

  it('preserves A -> B -> A visits when returning to same camera after > 120s', () => {
    const events: EventLite[] = [
      {
        event_id: 'a1',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:00:00.000000Z',
        threat_score: 30,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'b1',
        camera_id: 'CAM-02',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:02:00.000000Z',
        threat_score: 40,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'a2',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:05:00.000000Z',
        threat_score: 50,
        plate: 'KA01AB1234',
      },
    ];

    const journey = buildJourney(events);
    expect(journey.sightings).toHaveLength(3);
    expect(journey.sightings.map(s => s.camera_id)).toEqual(['CAM-01', 'CAM-02', 'CAM-01']);
    expect(journey.transitions).toHaveLength(2);
    expect(journey.transitions[0]?.from).toBe('CAM-01');
    expect(journey.transitions[0]?.to).toBe('CAM-02');
    expect(journey.transitions[1]?.from).toBe('CAM-02');
    expect(journey.transitions[1]?.to).toBe('CAM-01');
  });

  it('orders unsorted input and microsecond differences correctly and deterministically', () => {
    const events: EventLite[] = [
      {
        event_id: 'e2',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:00:00.000002Z',
        threat_score: 30,
        plate: 'KA01AB1234',
      },
      {
        event_id: 'e1',
        camera_id: 'CAM-01',
        event_type: 'VEHICLE_DETECTED',
        timestamp: '2026-10-25T10:00:00.000001Z',
        threat_score: 30,
        plate: 'KA01AB1234',
      },
    ];

    const journey = buildJourney(events);
    expect(journey.sightings[0]?.event_ids).toEqual(['e1', 'e2']);
    expect(journey.sightings[0]?.first_seen).toBe('2026-10-25T10:00:00.000001Z');
    expect(journey.sightings[0]?.last_seen).toBe('2026-10-25T10:00:00.000002Z');
  });

  it('returns empty journey on empty input without error', () => {
    const journey = buildJourney([]);
    expect(journey).toEqual({
      sightings: [],
      transitions: [],
      total_events: 0,
      span_s: 0,
      plate_variants: [],
    });
  });

  it('correctly converts ISO to microseconds', () => {
    const micros = isoToMicros('2026-10-25T10:00:00.123456Z');
    expect(micros).toBeGreaterThan(0n);
    expect(isoToMicros('2026-10-25T10:00:00.123457Z') - micros).toBe(1n);

    expect(() => isoToMicros('invalid-date')).toThrow();
  });
});
