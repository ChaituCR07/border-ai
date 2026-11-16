import fs from 'node:fs';
import path from 'node:path';
import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Pool } = pg;

function resolveDatabaseConfig(): pg.PoolConfig {
  if (process.env.DATABASE_URL) {
    return { connectionString: process.env.DATABASE_URL };
  }

  const host = process.env.DB_HOST || 'localhost';
  const port = Number(process.env.DB_PORT || 5432);
  const database = process.env.DB_NAME || 'border_ai';
  const user = process.env.DB_USER || 'postgres';

  let password = process.env.DB_PASSWORD || '';
  if (process.env.DATABASE_URL_FILE && fs.existsSync(process.env.DATABASE_URL_FILE)) {
    password = fs.readFileSync(process.env.DATABASE_URL_FILE, 'utf8').trim();
  } else if (!password) {
    const adminSecret = '/run/secrets/pg_admin_password';
    if (fs.existsSync(adminSecret)) {
      password = fs.readFileSync(adminSecret, 'utf8').trim();
    } else {
      password = 'postgres';
    }
  }

  return { host, port, database, user, password };
}

async function runMigrations() {
  const poolConfig = resolveDatabaseConfig();
  console.log('[migrate] Connecting to database...');
  const pool = new Pool(poolConfig);

  try {
    const client = await pool.connect();
    try {
      await client.query(`
        CREATE TABLE IF NOT EXISTS schema_migrations (
          migration text PRIMARY KEY,
          applied_at timestamptz NOT NULL DEFAULT now()
        );
      `);

      const migrationsDir = path.resolve(process.cwd(), '../database/migrations');
      const targetDir = fs.existsSync(migrationsDir)
        ? migrationsDir
        : path.resolve(process.cwd(), 'database/migrations');

      if (!fs.existsSync(targetDir)) {
        throw new Error(`Migrations directory not found at ${targetDir}`);
      }

      const files = fs.readdirSync(targetDir).filter(f => f.endsWith('.sql')).sort();
      const { rows } = await client.query('SELECT migration FROM schema_migrations');
      const applied = new Set(rows.map(r => r.migration));

      let count = 0;
      for (const file of files) {
        if (!applied.has(file)) {
          console.log(`[migrate] Applying ${file}...`);
          const sql = fs.readFileSync(path.join(targetDir, file), 'utf-8');
          await client.query('BEGIN');
          try {
            await client.query(sql);
            await client.query('INSERT INTO schema_migrations (migration) VALUES ($1)', [file]);
            await client.query('COMMIT');
            console.log(`[migrate] ✓ Applied ${file}`);
            count++;
          } catch (err) {
            await client.query('ROLLBACK');
            throw err;
          }
        }
      }

      console.log(`[migrate] Completed successfully. Applied ${count} migration(s).`);
    } finally {
      client.release();
    }
  } catch (err: any) {
    console.error('[migrate] Migration error:', err.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

runMigrations();
