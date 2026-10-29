import pg from 'pg';

export async function seedJourneyFixtures(pool: pg.Pool) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // 1. Plan acceptance journey: CAM-03 -> CAM-04 -> CAM-05
    // Event 1: CAM-03 at 10:00:00
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
      VALUES (
        '10000000-0000-0000-0000-000000000001',
        'CAM-03',
        'VEHICLE_DETECTED',
        50,
        'MEDIUM',
        '2026-10-25T10:00:00.000000Z',
        'KA01AB1234',
        '{"vehicle_id": "VEH-100"}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    // Event 2: CAM-03 at 10:00:10 (+10s, merges into Sighting 1)
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
      VALUES (
        '10000000-0000-0000-0000-000000000002',
        'CAM-03',
        'ANPR_MATCH',
        75,
        'HIGH',
        '2026-10-25T10:00:10.000000Z',
        'KA01AB1234',
        '{"vehicle_id": "VEH-100"}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    // Event 3: CAM-04 at 10:00:38 (+28s transition from CAM-03, OCR lookalike KA0IAB1234)
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
      VALUES (
        '10000000-0000-0000-0000-000000000003',
        'CAM-04',
        'VEHICLE_DETECTED',
        60,
        'HIGH',
        '2026-10-25T10:00:38.000000Z',
        'KA0IAB1234',
        '{"vehicle_id": "VEH-100"}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    // Event 4: CAM-05 at 10:01:50 (+72s transition from CAM-04)
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
      VALUES (
        '10000000-0000-0000-0000-000000000004',
        'CAM-05',
        'RESTRICTED_ZONE_ENTRY',
        90,
        'CRITICAL',
        '2026-10-25T10:01:50.000000Z',
        'KA01AB1234',
        '{"vehicle_id": "VEH-100"}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    // 2. Burst: 40 events in 30s on CAM-01
    const burstBase = new Date('2026-10-25T14:00:00.000Z').getTime();
    for (let i = 0; i < 40; i++) {
      const ts = new Date(burstBase + (i * 30000) / 40).toISOString();
      const uuid = `20000000-0000-0000-0000-${i.toString().padStart(12, '0')}`;
      await client.query(`
        INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
        VALUES ($1, 'CAM-01', 'VEHICLE_DETECTED', 40, 'LOW', $2, 'DL01AB9999', '{}'::jsonb)
        ON CONFLICT (event_id) DO NOTHING;
      `, [uuid, ts]);
    }

    // 3. Time-of-day night window testing (22:00 -> 05:00 UTC)
    // Night event 1: 23:30 UTC
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
      VALUES (
        '30000000-0000-0000-0000-000000000001',
        'CAM-02',
        'VEHICLE_DETECTED',
        65,
        'HIGH',
        '2026-10-25T23:30:00.000000Z',
        'MH12CD5678',
        '{}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    // Daytime event: 14:00 UTC (excluded by 22:00 -> 05:00 window)
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, plate_number, metadata)
      VALUES (
        '30000000-0000-0000-0000-000000000002',
        'CAM-02',
        'VEHICLE_DETECTED',
        40,
        'MEDIUM',
        '2026-10-25T14:00:00.000000Z',
        'MH12CD5678',
        '{}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    // 4. Person identifier events
    await client.query(`
      INSERT INTO events (event_id, camera_id, event_type, threat_score, severity, timestamp, metadata)
      VALUES (
        '40000000-0000-0000-0000-000000000001',
        'CAM-01',
        'PERSON_DETECTED',
        85,
        'HIGH',
        '2026-10-25T11:00:00.000000Z',
        '{"person_id": "PER-1002", "subject_id": "PER-1002"}'::jsonb
      ) ON CONFLICT (event_id) DO NOTHING;
    `);

    await client.query('COMMIT');
    console.log('Successfully seeded golden journey & forensic search fixtures.');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const pool = new pg.Pool({
    connectionString: process.env.DATABASE_URL || 'postgres://border_api:border_api_dev@localhost:5432/border_ai',
  });
  seedJourneyFixtures(pool)
    .then(() => pool.end())
    .catch((err) => {
      console.error('Failed to seed fixtures:', err);
      process.exit(1);
    });
}
