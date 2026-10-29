import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  plateNorm,
  plateKey,
  escapeLike,
  classifyPlateMatch,
  type PlateMatch,
} from '../../src/common/plate.js';

describe('Plate Normalisation & OCR Look-Alike (Unit & Parity)', () => {
  it('plateNorm cleans uppercase alphanumeric characters and strips whitespace/punctuation', () => {
    expect(plateNorm('ka 01-ab 1234')).toBe('KA01AB1234');
    expect(plateNorm('   dl_04.gh-9999   ')).toBe('DL04GH9999');
    expect(plateNorm('  ---  ')).toBe('');
    expect(plateNorm('')).toBe('');
  });

  it('plateKey maps confusable characters to canonical classes', () => {
    expect(plateKey('KA0IAB1234')).toBe(plateKey('KA01AB1234'));
    expect(plateKey('KAO1AB1234')).toBe(plateKey('KA01AB1234'));
    expect(plateKey('KA01A81234')).toBe(plateKey('KA01AB1234'));
    expect(plateKey('KA01AB1234')).not.toBe(plateKey('KA01AB1235'));
  });

  it('escapeLike escapes LIKE metacharacters % and _ and backslash', () => {
    expect(escapeLike('KA_1%')).toBe('KA\\_1\\%');
    expect(escapeLike('test\\case%_')).toBe('test\\\\case\\%\\_');
  });

  it('conforms 100% to shared fixture plate_matching_cases.json', () => {
    const fixturePath = path.resolve(__dirname, '../../../docs/fixtures/plate_matching_cases.json');
    expect(fs.existsSync(fixturePath)).toBe(true);

    const cases = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));

    for (const c of cases) {
      const mode = (c.mode ?? 'lookalike') as PlateMatch;
      const actual = classifyPlateMatch(c.query, c.candidate, mode);
      expect(actual, `Failed for query="${c.query}", candidate="${c.candidate}", mode="${mode}"`).toBe(c.expect);
    }
  });
});
