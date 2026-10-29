import { describe, it, expect } from 'vitest';
import { csvCell } from '../../src/common/csv.js';

describe('CSV cell sanitization & formula injection protection', () => {
  it('returns empty string for null and undefined', () => {
    expect(csvCell(null)).toBe('');
    expect(csvCell(undefined)).toBe('');
  });

  it('prepends single quote to cells beginning with formula triggers (=, +, -, @, \\t, \\r)', () => {
    expect(csvCell('=SUM(A1:B10)')).toBe("'=SUM(A1:B10)");
    expect(csvCell('+cmd')).toBe("'+cmd");
    expect(csvCell('-100')).toBe("'-100");
    expect(csvCell('@IMPORTXML(...)')).toBe("'@IMPORTXML(...)");
    expect(csvCell('\ttab_prefixed')).toBe("'\ttab_prefixed");
  });

  it('quotes cells containing commas, quotes, or newlines, escaping quotes', () => {
    expect(csvCell('hello, world')).toBe('"hello, world"');
    expect(csvCell('hello "world"')).toBe('"hello ""world"""');
    expect(csvCell('line1\nline2')).toBe('"line1\nline2"');
    expect(csvCell('=cmd|"/C calc"!A0')).toBe('"\'=cmd|""/C calc""!A0"');
  });

  it('leaves benign strings unquoted and unprefixed', () => {
    expect(csvCell('KA01AB1234')).toBe('KA01AB1234');
    expect(csvCell('CAM-01')).toBe('CAM-01');
    expect(csvCell(42)).toBe('42');
  });
});
