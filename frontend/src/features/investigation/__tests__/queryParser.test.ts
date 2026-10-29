import { describe, it, expect } from 'vitest';
import { parseOmniboxQuery, formatQueryTokens } from '../queryParser.js';

describe('queryParser (omnibox token extraction)', () => {
  it('extracts tokens for cam, type, sev, score, and plate', () => {
    const query = 'cam:CAM-01,CAM-02 type:VEHICLE_DETECTED sev:CRITICAL score:>75 plate:KA01*';
    const { tokens, state } = parseOmniboxQuery(query);

    expect(tokens).toHaveLength(5);
    expect(state.camera_id).toEqual(['CAM-01', 'CAM-02']);
    expect(state.event_type).toEqual(['VEHICLE_DETECTED']);
    expect(state.severity).toEqual(['CRITICAL']);
    expect(state.min_score).toBe(76);
    expect(state.plate).toBe('KA01');
    expect(state.plate_match).toBe('prefix');
  });

  it('classifies standalone UUID as selected_event_id', () => {
    const uuid = '11111111-2222-3333-4444-555555555555';
    const { state } = parseOmniboxQuery(uuid);
    expect(state.selected_event_id).toBe(uuid);
  });

  it('classifies standalone Indian plate format as plate with lookalike match', () => {
    const { state } = parseOmniboxQuery('MH12CD5678');
    expect(state.plate).toBe('MH12CD5678');
    expect(state.plate_match).toBe('lookalike');
  });

  it('retains arbitrary free text in q', () => {
    const { state, freeText } = parseOmniboxQuery('cam:CAM-03 intruder near fence');
    expect(state.camera_id).toEqual(['CAM-03']);
    expect(freeText).toBe('intruder near fence');
    expect(state.q).toBe('intruder near fence');
  });

  it('formats active search state into omnibox query string', () => {
    const formatted = formatQueryTokens({
      camera_id: ['CAM-01'],
      severity: ['CRITICAL'],
      min_score: 80,
      plate: 'KA01AB1234',
      plate_match: 'lookalike',
    });
    expect(formatted).toBe('cam:CAM-01 sev:CRITICAL score:>=80 plate:KA01AB1234');
  });
});
