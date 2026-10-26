import { describe, it, expect } from 'vitest';
import { formatPlateDisplay } from './plate';

describe('formatPlateDisplay', () => {
  it('formats standard 10-char Indian license plates', () => {
    expect(formatPlateDisplay('KA01AB1234')).toBe('KA 01 AB 1234');
    expect(formatPlateDisplay('DL05C9999')).toBe('DL 05 C 9999');
    expect(formatPlateDisplay('MH12DE1433')).toBe('MH 12 DE 1433');
  });

  it('handles null, undefined or empty strings safely', () => {
    expect(formatPlateDisplay(null)).toBe('–');
    expect(formatPlateDisplay(undefined)).toBe('–');
    expect(formatPlateDisplay('')).toBe('–');
  });

  it('preserves non-standard or international plates without distortion', () => {
    expect(formatPlateDisplay('CUSTOM-PLATE')).toBe('CUSTOM-PLATE');
  });
});
