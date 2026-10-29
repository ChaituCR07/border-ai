import { describe, it, expect } from 'vitest';
import {
  parseSearchParams,
  serializeSearchParams,
  type InvestigationSearchState,
} from '../searchSchema.js';

describe('searchSchema URL serialization & deserialization', () => {
  it('round-trips full investigation search state', () => {
    const original: InvestigationSearchState = {
      q: 'suspicious',
      camera_id: ['CAM-01', 'CAM-02'],
      event_type: ['VEHICLE_DETECTED', 'RESTRICTED_ZONE_ENTRY'],
      severity: ['CRITICAL', 'HIGH'],
      min_score: 50,
      max_score: 95,
      from: '2026-10-25T00:00:00.000Z',
      to: '2026-10-25T23:59:59.000Z',
      plate: 'KA01AB1234',
      plate_match: 'prefix',
      vehicle_id: 'VEH-99',
      person_id: 'PER-42',
      time_from: '22:00',
      time_to: '04:00',
      tz: 'Asia/Kolkata',
      sort: 'score',
      view: 'timeline',
      selected_event_id: '11111111-1111-1111-1111-111111111111',
    };

    const params = serializeSearchParams(original);
    const restored = parseSearchParams(params);

    expect(restored).toEqual(original);
  });

  it('never serializes purpose into URL params', () => {
    const stateWithPurpose: any = {
      q: 'border patrol',
      purpose: 'Confidential investigation 99',
    };

    const params = serializeSearchParams(stateWithPurpose);
    expect(params.has('purpose')).toBe(false);
    expect(params.toString()).not.toContain('Confidential');
  });

  it('drops invalid severity values during parsing', () => {
    const params = new URLSearchParams('severity=CRITICAL,INVALID_SEV,LOW');
    const state = parseSearchParams(params);
    expect(state.severity).toEqual(['CRITICAL', 'LOW']);
  });
});
