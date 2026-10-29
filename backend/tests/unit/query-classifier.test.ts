import { describe, it, expect } from 'vitest';
import { classifyOmniboxQuery } from '../../src/modules/investigation/query-classifier.js';
import { AppError } from '../../src/common/errors.js';

describe('Server-side Omnibox Query Classifier', () => {
  it('classifies 36-char UUID as eventId', () => {
    const res = classifyOmniboxQuery('0192e2b3-6c8a-7e1b-bf3d-246e4912ab01');
    expect(res).toEqual({ eventId: '0192e2b3-6c8a-7e1b-bf3d-246e4912ab01' });
  });

  it('classifies camera expressions (CAM-03, cam_4, CAM5) as normalized cameraId', () => {
    expect(classifyOmniboxQuery('CAM-03')).toEqual({ cameraId: 'CAM-03' });
    expect(classifyOmniboxQuery('cam_4')).toEqual({ cameraId: 'CAM-04' });
    expect(classifyOmniboxQuery('CAM5')).toEqual({ cameraId: 'CAM-05' });
  });

  it('classifies plate-like strings (digit + letter, 4-16 chars) as plate with lookalike match', () => {
    expect(classifyOmniboxQuery('KA01AB1234')).toEqual({
      plate: 'KA01AB1234',
      plateMatch: 'lookalike',
    });
    expect(classifyOmniboxQuery('mh 12 cd 5678')).toEqual({
      plate: 'MH12CD5678',
      plateMatch: 'lookalike',
    });
  });

  it('classifies event type tokens as eventType', () => {
    expect(classifyOmniboxQuery('RESTRICTED_ZONE_ENTRY')).toEqual({
      eventType: 'RESTRICTED_ZONE_ENTRY',
    });
    expect(classifyOmniboxQuery('restricted')).toEqual({
      eventType: 'RESTRICTED_ZONE_ENTRY',
    });
    expect(classifyOmniboxQuery('watchlist')).toEqual({
      eventType: 'WATCHLIST_HIT',
    });
  });

  it('returns empty classification for blank or empty query', () => {
    expect(classifyOmniboxQuery('')).toEqual({});
    expect(classifyOmniboxQuery('   ')).toEqual({});
  });

  it('throws 400 with helpful message for uninterpretable garbage', () => {
    expect(() => classifyOmniboxQuery('???!!!')).toThrow(AppError);
    try {
      classifyOmniboxQuery('???!!!');
    } catch (err: any) {
      expect(err.status).toBe(400);
      expect(err.message).toContain("Could not interpret '???!!!'");
    }
  });
});
