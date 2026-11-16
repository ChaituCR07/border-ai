import fs from 'node:fs';
import pg from 'pg';

function readSecret(name: string, fallback: string): string {
  const secretPath = `/run/secrets/${name}`;
  if (fs.existsSync(secretPath)) {
    return fs.readFileSync(secretPath, 'utf8').trim();
  }
  const envVal = process.env[name.toUpperCase()];
  return envVal || fallback;
}

async function main() {
  console.log('[DB-INIT] Starting database role and privilege initialization...');

  const host = process.env.DB_HOST || 'localhost';
  const port = Number(process.env.DB_PORT || 5432);
  const database = process.env.DB_NAME || 'border_ai';
  const adminPassword = readSecret('pg_admin_password', 'postgres');

  const pool = new pg.Pool({
    host,
    port,
    database,
    user: 'postgres',
    password: adminPassword,
    connectionTimeoutMillis: 5000,
  });

  const client = await pool.connect();
  try {
    const apiPass = readSecret('pg_api_password', 'api_secret_2026');
    const enginePass = readSecret('pg_engine_password', 'engine_secret_2026');
    const sinkPass = readSecret('pg_sink_password', 'sink_secret_2026');
    const retentionPass = readSecret('pg_retention_password', 'retention_secret_2026');

    console.log('[DB-INIT] Ensuring least-privilege service roles exist...');

    // Helper to safely create or update role password
    const upsertRole = async (role: string, pass: string) => {
      await client.query(`
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${role}') THEN
            CREATE ROLE ${role} WITH LOGIN PASSWORD '${pass}';
          ELSE
            ALTER ROLE ${role} WITH PASSWORD '${pass}';
          END IF;
        END
        $$;
      `);
    };

    await upsertRole('border_api', apiPass);
    await upsertRole('border_engine', enginePass);
    await upsertRole('border_sink', sinkPass);
    await upsertRole('border_retention', retentionPass);

    console.log('[DB-INIT] Applying least-privilege table grants...');

    // 1. Core database connection
    await client.query(`
      GRANT CONNECT ON DATABASE ${database} TO border_api, border_engine, border_sink, border_retention;
      GRANT USAGE ON SCHEMA public TO border_api, border_engine, border_sink, border_retention;
    `);

    // 2. border_api grants (Full API domain access)
    await client.query(`
      GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO border_api;
      GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO border_api;
      ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO border_api;
      ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO border_api;
    `);

    // 3. border_engine grants: Cameras, configs, rules ONLY. STRICTLY NO access to users/sessions!
    await client.query(`
      REVOKE ALL ON ALL TABLES IN SCHEMA public FROM border_engine;
      DO $$
      BEGIN
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'cameras') THEN
          GRANT SELECT ON TABLE cameras TO border_engine;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'config_versions') THEN
          GRANT SELECT ON TABLE config_versions TO border_engine;
        END IF;
      END $$;
    `);

    // 4. border_sink grants: Ingestion sink inserting events and detections. NO access to users/sessions!
    await client.query(`
      REVOKE ALL ON ALL TABLES IN SCHEMA public FROM border_sink;
      DO $$
      BEGIN
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'events') THEN
          GRANT INSERT, SELECT ON TABLE events TO border_sink;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'alerts') THEN
          GRANT INSERT, SELECT ON TABLE alerts TO border_sink;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'camera_status') THEN
          GRANT INSERT, SELECT ON TABLE camera_status TO border_sink;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'api_audit_log') THEN
          GRANT INSERT, SELECT ON TABLE api_audit_log TO border_sink;
        END IF;
      END $$;
      GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO border_sink;
    `);

    // 5. border_retention grants: Pruning expired records + auditing
    await client.query(`
      REVOKE ALL ON ALL TABLES IN SCHEMA public FROM border_retention;
      DO $$
      BEGIN
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'events') THEN
          GRANT SELECT, DELETE ON TABLE events TO border_retention;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'alerts') THEN
          GRANT SELECT, DELETE ON TABLE alerts TO border_retention;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'camera_status') THEN
          GRANT SELECT, DELETE ON TABLE camera_status TO border_retention;
        END IF;
        IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'api_audit_log') THEN
          GRANT INSERT, SELECT ON TABLE api_audit_log TO border_retention;
        END IF;
      END $$;
      GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO border_retention;
    `);

    console.log('[DB-INIT] Successfully configured all roles with strict least-privilege boundaries.');
    process.exit(0);
  } catch (err: any) {
    console.error('[DB-INIT FATAL] Role initialization failed:', err?.message || err);
    process.exit(1);
  } finally {
    client.release();
    await pool.end().catch(() => {});
  }
}

main();
