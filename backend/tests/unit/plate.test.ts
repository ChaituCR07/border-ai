import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { normalisePlate, cleanPlateText } from '../../src/common/plate.js';

describe('Plate Normalizer', () => {
  it('cleans text stripping spaces, punctuation, and uppercase conversion', () => {
    expect(cleanPlateText('ka - 01 ab 1234')).toBe('KA01AB1234');
  });

  it('corrects OCR letter-to-digit lookalikes for Indian registration', () => {
    expect(normalisePlate('KAO1AB1234')).toBe('KA01AB1234');
  });

  it('passes all cross-language test fixtures identically to Python', () => {
    const fixturePath = path.resolve(__dirname, '../fixtures/plate_normalization.json');
    const fixtures: { input: string; expected: string }[] = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));

    for (const testCase of fixtures) {
      const actual = normalisePlate(testCase.input);
      expect(actual).toBe(testCase.expected);
    }
  });
});
