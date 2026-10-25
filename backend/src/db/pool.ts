import pg from 'pg';

// Keep microsecond precision and 64-bit integers as lossless raw strings.
pg.types.setTypeParser(1184, (v: string) => v); // timestamptz
pg.types.setTypeParser(1114, (v: string) => v); // timestamp
pg.types.setTypeParser(20, (v: string) => v);   // int8 / bigint

export function createPool(connectionString: string): pg.Pool {
  const pool = new pg.Pool({
    connectionString,
    max: 15,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
  });

  pool.on('connect', (client) => {
    client.query("SET TIME ZONE 'UTC'").catch((err) => {
      console.error('Failed to set UTC timezone on pg client', err);
    });
  });

  pool.on('error', (err) => {
    console.error('Unexpected error on idle pg client', err);
  });

  return pool;
}
