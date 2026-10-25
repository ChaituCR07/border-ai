import { randomUUID } from 'node:crypto';
import pg from 'pg';
import { loadConfig } from '../src/config/env.js';

interface SeedOptions {
  events: number;
  cameras: number;
  days: number;
}

function parseArgs(): SeedOptions {
  const args = process.argv.slice(2);
  const opts: SeedOptions = { events: 1000, cameras: 6, days: 7 };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--events' && args[i + 1]) opts.events = parseInt(args[++i]!, 10);
    else if (args[i] === '--cameras' && args[i + 1]) opts.cameras = parseInt(args[++i]!, 10);
    else if (args[i] === '--days' && args[i + 1]) opts.days = parseInt(args[++i]!, 10);
  }
  return opts;
}

async function main() {
  const config = loadConfig();
  const opts = parseArgs();
  const pool = new pg.Pool({ connectionString: config.DATABASE_URL });

  console.log(`Seeding ${opts.events} synthetic events across ${opts.cameras} cameras over ${opts.days} days...`);

  // 1. Seed Cameras
  const cameraIds: string[] = [];
  for (let i = 1; i <= opts.cameras; i++) {
    const camId = `CAM-${String(i).padStart(2, '0')}`;
    cameraIds.push(camId);
    await pool.query(`
      INSERT INTO cameras (camera_id, name, location, location_label, rtsp_url, enabled, updated_at)
      VALUES ($1, $2, $3, $3, $4, true, now())
      ON CONFLICT (camera_id) DO UPDATE SET enabled = true;
    `, [
      camId,
      `Border Gate ${i} - Sector ${Math.ceil(i / 2)}`,
      `Sector ${Math.ceil(i / 2)}, Km ${i * 4}`,
      `rtsp://10.0.1.${10 + i}:554/live`,
    ]);
  }

  // 2. Sample plates and event types
  const samplePlates = ['KA01AB1234', 'DL02CD5678', 'MH12DE1433', 'GJ05JA5050', 'HR26DK8888', 'KA04MS9000'];
  const eventTypes = ['LINE_CROSSING', 'RESTRICTED_ZONE_ENTRY', 'LOITERING', 'ANPR_WATCHLIST_HIT', 'UNATTENDED_OBJECT'];
  const severities = [
    { name: 'LOW', weight: 60, scoreRange: [0, 29] },
    { name: 'MEDIUM', weight: 25, scoreRange: [30, 59] },
    { name: 'HIGH', weight: 12, scoreRange: [60, 79] },
    { name: 'CRITICAL', weight: 3, scoreRange: [80, 100] },
  ];

  const nowMs = Date.now();
  const spanMs = opts.days * 24 * 60 * 60 * 1000;

  for (let i = 0; i < opts.events; i++) {
    const eventId = randomUUID();
    const camId = cameraIds[Math.floor(Math.random() * cameraIds.length)]!;
    const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)]!;

    // Weighted severity
    const rand = Math.random() * 100;
    let acc = 0;
    let chosen = severities[0]!;
    for (const s of severities) {
      acc += s.weight;
      if (rand <= acc) { chosen = s; break; }
    }

    const threatScore = Math.floor(Math.random() * (chosen.scoreRange[1] - chosen.scoreRange[0] + 1)) + chosen.scoreRange[0];
    const plate = Math.random() < 0.6 ? samplePlates[Math.floor(Math.random() * samplePlates.length)] : null;
    const offsetMs = Math.floor(Math.random() * spanMs);
    const ts = new Date(nowMs - offsetMs).toISOString();

    const metadata = {
      synthetic: true,
      plate,
      explanation: {
        factors: [
          { name: eventType.toLowerCase(), points: Math.floor(threatScore * 0.6) },
          { name: 'speed_anomaly', points: Math.floor(threatScore * 0.4) },
        ],
      },
    };

    await pool.query(`
      INSERT INTO events (event_id, camera_id, track_id, event_type, severity, threat_score, timestamp, plate_number, metadata)
      VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz, $8, $9::jsonb)
      ON CONFLICT (event_id) DO NOTHING;
    `, [
      eventId,
      camId,
      Math.floor(Math.random() * 1000) + 1,
      eventType,
      chosen.name,
      threatScore,
      ts,
      plate,
      JSON.stringify(metadata),
    ]);

    // Create alerts for CRITICAL and some HIGH
    if (chosen.name === 'CRITICAL' || (chosen.name === 'HIGH' && Math.random() < 0.5)) {
      const alertId = randomUUID();
      await pool.query(`
        INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, status, created_at)
        VALUES ($1, $2, $3, $4, $5, 'NEW', $6::timestamptz)
        ON CONFLICT (event_id) DO NOTHING;
      `, [alertId, eventId, camId, chosen.name, threatScore, ts]);
    }

    if ((i + 1) % 250 === 0 || i === opts.events - 1) {
      console.log(`Seeded ${i + 1}/${opts.events} events...`);
    }
  }

  console.log('Seeding completed successfully!');
  await pool.end();
}

main().catch(err => {
  console.error('Seeding failed:', err);
  process.exit(1);
});
