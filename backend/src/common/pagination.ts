import { AppError } from './errors.js';

export interface Cursor {
  t: string;  // ISO timestamp with microsecond precision
  id: string; // UUID of entity
}

export interface PaginationMeta {
  limit: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export function encodeCursor(c: Cursor): string {
  return Buffer.from(JSON.stringify(c)).toString('base64url');
}

export function decodeCursor(raw: string): Cursor {
  try {
    const json = JSON.parse(Buffer.from(raw, 'base64url').toString('utf8'));
    if (!json || typeof json.t !== 'string' || typeof json.id !== 'string') {
      throw new Error('Malformed cursor payload');
    }
    return { t: json.t, id: json.id };
  } catch {
    throw new AppError(400, 'VALIDATION_ERROR', 'Invalid cursor format');
  }
}

export function clampLimit(n: number | undefined, def = 50, max = 200): number {
  if (n === undefined || n === null || isNaN(n)) return def;
  return Math.min(Math.max(n, 1), max);
}
