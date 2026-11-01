import type pg from 'pg';
import { CameraLink, TopologyIndex } from './topology.js';
import { CameraTopologyNode, CorrelationRepo, TopologyData, SequenceSearchFilters } from './repo.js';
import { SequenceMatch, SequenceHop, sequenceSql, verifySequenceHops } from './sequence.js';
import { isoToMicros } from '../investigation/journey.js';
import { round3 } from './link.js';

export class PgCorrelationRepo implements CorrelationRepo {
  constructor(private readonly pool: pg.Pool) {}

  async getTopology(): Promise<TopologyData> {
    const camRes = await this.pool.query<{
      camera_id: string;
      name: string;
      location_label: string;
      map_x: string | number | null;
      map_y: string | number | null;
    }>(`
      SELECT camera_id, name, location_label, map_x, map_y
      FROM cameras
      ORDER BY camera_id ASC
    `);

    const linkRes = await this.pool.query<{
      from_camera: string;
      to_camera: string;
      min_s: number;
      typical_s: number;
      max_s: number;
      direction: 'both' | 'a_to_b';
      overlap: boolean;
    }>(`
      SELECT from_camera, to_camera, min_s, typical_s, max_s, direction, overlap
      FROM camera_links
      ORDER BY from_camera ASC, to_camera ASC
    `);

    const cameras: CameraTopologyNode[] = camRes.rows.map(row => ({
      camera_id: row.camera_id,
      name: row.name,
      location_label: row.location_label,
      map_x: row.map_x != null ? Number(row.map_x) : 0,
      map_y: row.map_y != null ? Number(row.map_y) : 0,
    }));

    const links: CameraLink[] = linkRes.rows.map(row => ({
      a: row.from_camera,
      b: row.to_camera,
      min_s: row.min_s,
      typical_s: row.typical_s,
      max_s: row.max_s,
      direction: row.direction,
      overlap: row.overlap,
    }));

    const topo = new TopologyIndex(links);
    return {
      version: topo.version,
      cameras,
      links,
    };
  }

  async seedTopology(
    cameras: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }>,
    links: CameraLink[]
  ): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      for (const [camId, coords] of Object.entries(cameras)) {
        await client.query(
          `
          INSERT INTO cameras (camera_id, name, location_label, map_x, map_y)
          VALUES ($1, $2, $3, $4, $5)
          ON CONFLICT (camera_id) DO UPDATE
          SET map_x = EXCLUDED.map_x,
              map_y = EXCLUDED.map_y,
              name = COALESCE(cameras.name, EXCLUDED.name),
              location_label = COALESCE(cameras.location_label, EXCLUDED.location_label)
        `,
          [
            camId,
            coords.name ?? `Camera ${camId}`,
            coords.location_label ?? `Checkpoint ${camId}`,
            coords.map_x,
            coords.map_y,
          ]
        );
      }

      await client.query('DELETE FROM camera_links');
      for (const link of links) {
        await client.query(
          `
          INSERT INTO camera_links (from_camera, to_camera, min_s, typical_s, max_s, direction, overlap)
          VALUES ($1, $2, $3, $4, $5, $6, $7)
        `,
          [
            link.a,
            link.b,
            link.min_s,
            link.typical_s,
            link.max_s,
            link.direction ?? 'both',
            !!link.overlap,
          ]
        );
      }

      await client.query('COMMIT');
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  async sequenceSearch(filters: SequenceSearchFilters): Promise<SequenceMatch[]> {
    const steps = filters.cameras.length;
    const sql = sequenceSql(steps);
    const params = [
      ...filters.cameras,
      filters.from,
      filters.to,
      filters.maxHopGapS,
      filters.limit,
    ];

    const res = await this.pool.query(sql, params);
    const matches: SequenceMatch[] = [];

    for (const row of res.rows) {
      const hops: SequenceHop[] = [];
      for (let i = 0; i < steps; i++) {
        const cam = filters.cameras[i]!;
        const ts = row[`ts${i + 1}`];
        if (ts) {
          hops.push({
            camera_id: cam,
            timestamp: new Date(ts).toISOString(),
            event_id: `seq-${cam}-${row.plate_key}`,
          });
        }
      }

      if (verifySequenceHops(hops, filters.maxHopGapS)) {
        const variants: string[] = row.variants_first ?? [];
        const totalDuration = round3(
          Number(isoToMicros(hops.at(-1)!.timestamp) - isoToMicros(hops[0]!.timestamp)) / 1_000_000
        );

        matches.push({
          plate_key: row.plate_key,
          representative_plate: variants[0] ?? row.plate_key,
          plate_variants: variants,
          hops,
          total_duration_s: totalDuration,
        });
      }
    }

    return matches;
  }
}
