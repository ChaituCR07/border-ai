import fs from 'node:fs';
import path from 'node:path';
import pg from 'pg';
import {
  CameraTopologyConfigSchema,
  validateTopologyConfig,
  type CameraTopologyConfig,
} from './topology-check.js';

export async function seedTopology(pool: pg.Pool, filePath?: string): Promise<void> {
  let targetPath = filePath || path.resolve(process.cwd(), 'configs/camera_topology.json');
  if (!fs.existsSync(targetPath)) {
    const parentPath = path.resolve(process.cwd(), '../configs/camera_topology.json');
    if (fs.existsSync(parentPath)) {
      targetPath = parentPath;
    }
  }
  console.log(`[topology:seed] Seeding topology from ${targetPath}...`);

  if (!fs.existsSync(targetPath)) {
    throw new Error(`Topology config file not found: ${targetPath}`);
  }

  const raw = fs.readFileSync(targetPath, 'utf-8');
  const config: CameraTopologyConfig = CameraTopologyConfigSchema.parse(JSON.parse(raw));

  const validation = validateTopologyConfig(config);
  if (!validation.valid) {
    throw new Error(`Topology config failed validation:\n${validation.errors.join('\n')}`);
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // 1. Upsert cameras and their schematic coordinates (auto-register missing cameras)
    for (const [camId, coords] of Object.entries(config.cameras)) {
      await client.query(
        `INSERT INTO cameras (camera_id, name, location, map_x, map_y)
         VALUES ($1, $1, '', $2, $3)
         ON CONFLICT (camera_id) DO UPDATE
         SET map_x = EXCLUDED.map_x,
             map_y = EXCLUDED.map_y,
             updated_at = now();`,
        [camId, coords.map_x, coords.map_y]
      );
    }

    // 2. Upsert camera links
    for (const link of config.links) {
      await client.query(
        `INSERT INTO camera_links (camera_a, camera_b, min_s, typical_s, max_s, direction, overlap, notes)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         ON CONFLICT (camera_a, camera_b) DO UPDATE
         SET min_s = EXCLUDED.min_s,
             typical_s = EXCLUDED.typical_s,
             max_s = EXCLUDED.max_s,
             direction = EXCLUDED.direction,
             overlap = EXCLUDED.overlap,
             notes = EXCLUDED.notes,
             updated_at = now();`,
        [
          link.a,
          link.b,
          link.min_s,
          link.typical_s,
          link.max_s,
          link.direction ?? 'both',
          link.overlap ?? false,
          link.notes ?? null,
        ]
      );
    }

    await client.query('COMMIT');
    console.log(`[topology:seed] Successfully seeded ${Object.keys(config.cameras).length} cameras and ${config.links.length} links into DB.`);
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const connectionString = process.env.DATABASE_URL || 'postgres://border_api:border_api_dev@localhost:5432/border_ai';
  const pool = new pg.Pool({ connectionString });
  seedTopology(pool)
    .then(() => pool.end())
    .catch((err) => {
      console.error('[topology:seed] Failed:', err);
      pool.end();
      process.exit(1);
    });
}
