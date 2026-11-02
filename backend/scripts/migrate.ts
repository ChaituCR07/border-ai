import fs from 'node:fs';
import path from 'node:path';
import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Pool } = pg;

async function runMigrations() {
  const databaseUrl = process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/border_ai';
  console.log('[migrate] Connecting to database...');
  const pool = new Pool({ connectionString: databaseUrl });

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
