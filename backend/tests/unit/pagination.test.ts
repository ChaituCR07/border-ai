import { describe, it, expect } from 'vitest';
import { encodeCursor, decodeCursor, clampLimit } from '../../src/common/pagination.js';
import { AppError } from '../../src/common/errors.js';

describe('Pagination utilities', () => {
  it('encodes and decodes cursor correctly preserving microsecond timestamp and id', () => {
    const cursor = {
      t: '2026-10-25T02:13:42.481233Z',
      id: '0b0e9f1a-3a21-4d92-938b-117849ef92aa',
    };

    const encoded = encodeCursor(cursor);
    expect(typeof encoded).toBe('string');

    const decoded = decodeCursor(encoded);
    expect(decoded).toEqual(cursor);
  });

  it('throws AppError 400 when decoding invalid or tampered cursor', () => {
    expect(() => decodeCursor('invalid-base64-payload!!!')).toThrow(AppError);
    expect(() => decodeCursor(Buffer.from(JSON.stringify({ wrong: true })).toString('base64url'))).toThrow(AppError);
  });

  it('clamps limit to bounds 1..200 with default 50', () => {
    expect(clampLimit(undefined)).toBe(50);
    expect(clampLimit(null as any)).toBe(50);
    expect(clampLimit(10)).toBe(10);
    expect(clampLimit(0)).toBe(1);
    expect(clampLimit(-5)).toBe(1);
    expect(clampLimit(500)).toBe(200);
  });
});
