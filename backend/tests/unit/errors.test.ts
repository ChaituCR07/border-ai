import { describe, it, expect } from 'vitest';
import { AppError, notFound, conflict, validationError } from '../../src/common/errors.js';

describe('Error classes and helpers', () => {
  it('creates AppError with status, code, message, and details', () => {
    const err = new AppError(422, 'CUSTOM_CODE', 'Custom message', { field: 'name' });
    expect(err.status).toBe(422);
    expect(err.code).toBe('CUSTOM_CODE');
    expect(err.message).toBe('Custom message');
    expect(err.details).toEqual({ field: 'name' });
  });

  it('creates notFound error', () => {
    const err = notFound('Camera');
    expect(err.status).toBe(404);
    expect(err.code).toBe('NOT_FOUND');
    expect(err.message).toBe('Camera not found');
  });

  it('creates conflict error', () => {
    const err = conflict('Duplicate camera_id');
    expect(err.status).toBe(409);
    expect(err.code).toBe('CONFLICT');
  });

  it('creates validation error', () => {
    const err = validationError('Invalid input');
    expect(err.status).toBe(400);
    expect(err.code).toBe('VALIDATION_ERROR');
  });
});
