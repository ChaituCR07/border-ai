import { describe } from 'vitest';
import pg from 'pg';

export const TEST_DATABASE_URL =
  process.env.TEST_DATABASE_URL || 'postgres://border_api:border_api_secret@localhost:5432/borderai_test';

export function createTestPool(): pg.Pool {
  pg.types.setTypeParser(1184, (v: string) => v);
  pg.types.setTypeParser(1114, (v: string) => v);
  pg.types.setTypeParser(20, (v: string) => v);

  return new pg.Pool({
    connectionString: TEST_DATABASE_URL,
    max: 5,
    idleTimeoutMillis: 10000,
  });
}

export const describeDb = describe;
