import fs from 'node:fs';
import path from 'node:path';
import pg from 'pg';

export interface RetentionOptions {
  eventsDays: number;
  snapshotsDays: number;
  auditDays: number;
  dryRun?: boolean;
}

export interface RetentionResult {
  purgedEvents: number;
  purgedAlerts: number;
  purgedSnapshots: number;
}

export async function runRetentionCycle(
  pool: pg.Pool,
  snapshotDir: string,
  options: RetentionOptions
): Promise<RetentionResult> {
  const client = await pool.connect();
  let purgedEvents = 0;
  let purgedAlerts = 0;
  let purgedSnapshots = 0;

  try {
    const eventsCutoff = new Date(Date.now() - options.eventsDays * 86400 * 1000).toISOString();
    const snapshotsCutoffMs = Date.now() - options.snapshotsDays * 86400 * 1000;

    // 1. Purge expired events
    if (!options.dryRun) {
      const resEvents = await client.query(
        'DELETE FROM events WHERE timestamp < $1 RETURNING event_id',
        [eventsCutoff]
      );
      purgedEvents = resEvents.rowCount || 0;

      // 2. Purge expired alerts
      const resAlerts = await client.query(
        'DELETE FROM alerts WHERE created_at < $1 RETURNING alert_id',
        [eventsCutoff]
      );
      purgedAlerts = resAlerts.rowCount || 0;
    }

    // 3. Purge expired snapshot files from filesystem
    if (fs.existsSync(snapshotDir)) {
      const walkAndClean = (dir: string) => {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          if (entry.isDirectory()) {
            walkAndClean(fullPath);
          } else if (entry.isFile()) {
            const stat = fs.statSync(fullPath);
            if (stat.mtimeMs < snapshotsCutoffMs) {
              if (!options.dryRun) {
                fs.unlinkSync(fullPath);
              }
              purgedSnapshots++;
            }
          }
        }
      };
      try {
        walkAndClean(snapshotDir);
      } catch (e: any) {
        console.warn('[RETENTION WARN] Error scanning snapshot directory:', e?.message);
      }
    }

    // 4. Record audit entry
    if (!options.dryRun && (purgedEvents > 0 || purgedAlerts > 0 || purgedSnapshots > 0)) {
      await client.query(
        `INSERT INTO api_audit_log (actor, action, entity_type, entity_id, detail)
         VALUES ($1, $2, $3, $4, $5)`,
        [
          'service:retention',
          'retention.purge',
          'system',
          'retention-worker',
          JSON.stringify({
            purged_events: purgedEvents,
            purged_alerts: purgedAlerts,
            purged_snapshots: purgedSnapshots,
            older_than_days: options.eventsDays,
          }),
        ]
      );
    }

    return { purgedEvents, purgedAlerts, purgedSnapshots };
  } finally {
    client.release();
  }
}

async function main() {
  console.log('[RETENTION] Initializing data retention daemon loop...');

  const host = process.env.DB_HOST || 'localhost';
  const port = Number(process.env.DB_PORT || 5432);
  const database = process.env.DB_NAME || 'border_ai';
  const user = process.env.DB_USER || 'border_retention';

  let password = process.env.DB_PASSWORD || '';
  const passwordFile = process.env.DB_PASSWORD_FILE || '/run/secrets/pg_retention_password';
  if (fs.existsSync(passwordFile)) {
    password = fs.readFileSync(passwordFile, 'utf8').trim();
  }

  const pool = new pg.Pool({ host, port, database, user, password });

  const eventsDays = Number(process.env.RETENTION_EVENTS_DAYS || 30);
  const snapshotsDays = Number(process.env.RETENTION_SNAPSHOTS_DAYS || 14);
  const auditDays = Number(process.env.RETENTION_AUDIT_DAYS || 365);
  const snapshotDir = process.env.SNAPSHOT_DIR || '/data/snapshots';

  const runOnce = process.argv.includes('--once');

  let running = true;
  process.on('SIGTERM', () => {
    console.log('[RETENTION] Received SIGTERM, terminating loop cleanly...');
    running = false;
  });
  process.on('SIGINT', () => {
    running = false;
  });

  const execute = async () => {
    try {
      console.log(`[RETENTION] Running cycle: events > ${eventsDays}d, snapshots > ${snapshotsDays}d...`);
      const result = await runRetentionCycle(pool, snapshotDir, {
        eventsDays,
        snapshotsDays,
        auditDays,
      });
      console.log(
        `[RETENTION OK] Cycle complete: Purged ${result.purgedEvents} events, ${result.purgedAlerts} alerts, ${result.purgedSnapshots} snapshots.`
      );
    } catch (err: any) {
      console.error('[RETENTION ERROR] Execution failed:', err?.message || err);
    }
  };

  await execute();

  if (runOnce) {
    await pool.end();
    process.exit(0);
  }

  // Periodic daily execution loop (every 24h)
  const intervalMs = 24 * 3600 * 1000;
  const timer = setInterval(() => {
    if (running) {
      execute();
    } else {
      clearInterval(timer);
      pool.end().then(() => process.exit(0));
    }
  }, intervalMs);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
