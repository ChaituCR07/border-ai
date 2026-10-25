import type pg from 'pg';
import type { CamerasRepo, CameraFilters, CreateCameraDTO, UpdateCameraDTO } from './repo.js';
import type { CameraResource } from '../../types/domain.js';
import { pgTsToIso } from '../../common/time.js';

export class PgCamerasRepo implements CamerasRepo {
  constructor(
    private readonly pool: pg.Pool,
    private readonly mjpegBaseUrl: string
  ) {}

  private mapRow(row: any): CameraResource {
    return {
      camera_id: row.camera_id,
      name: row.name ?? null,
      location_label: row.location_label ?? row.location ?? null,
      stream_url: row.stream_url ?? row.rtsp_url ?? null,
      has_credentials: Boolean(row.credentials_ref),
      credentials_ref: row.credentials_ref ?? null,
      enabled: row.enabled ?? true,
      live_view_url: `${this.mjpegBaseUrl.replace(/\/+$/, '')}/cam/${row.camera_id}.mjpg`,
      created_at: pgTsToIso(row.created_at) ?? new Date().toISOString(),
      updated_at: pgTsToIso(row.updated_at) ?? new Date().toISOString(),
    };
  }

  async list(filters: CameraFilters): Promise<CameraResource[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (filters.enabled !== undefined) {
      where.push(`enabled = $${idx++}`);
      args.push(filters.enabled);
    }
    if (filters.q) {
      where.push(`(name ILIKE $${idx} OR location_label ILIKE $${idx} OR location ILIKE $${idx} OR camera_id ILIKE $${idx})`);
      args.push(`%${filters.q}%`);
      idx++;
    }

    const sql = `
      SELECT camera_id, name, location_label, location, rtsp_url AS stream_url, credentials_ref, enabled, created_at, updated_at
      FROM cameras
      ${where.length ? 'WHERE ' + where.join(' AND ') : ''}
      ORDER BY camera_id ASC
    `;

    const res = await this.pool.query(sql, args);
    return res.rows.map(r => this.mapRow(r));
  }

  async getById(cameraId: string): Promise<CameraResource | null> {
    const sql = `
      SELECT camera_id, name, location_label, location, rtsp_url AS stream_url, credentials_ref, enabled, created_at, updated_at
      FROM cameras
      WHERE camera_id = $1
    `;
    const res = await this.pool.query(sql, [cameraId]);
    return res.rows[0] ? this.mapRow(res.rows[0]) : null;
  }

  async create(dto: CreateCameraDTO): Promise<CameraResource> {
    const sql = `
      INSERT INTO cameras (camera_id, name, location_label, location, rtsp_url, credentials_ref, enabled, updated_at)
      VALUES ($1, $2, $3, COALESCE($3, ''), $4, $5, $6, now())
      RETURNING camera_id, name, location_label, location, rtsp_url AS stream_url, credentials_ref, enabled, created_at, updated_at
    `;
    const res = await this.pool.query(sql, [
      dto.camera_id,
      dto.name,
      dto.location_label ?? null,
      dto.stream_url ?? null,
      dto.credentials_ref ?? null,
      dto.enabled ?? true,
    ]);
    return this.mapRow(res.rows[0]);
  }

  async update(cameraId: string, dto: UpdateCameraDTO): Promise<CameraResource | null> {
    const sql = `
      UPDATE cameras
      SET name = $2, location_label = $3, location = COALESCE($3, location), rtsp_url = $4, credentials_ref = $5, enabled = $6, updated_at = now()
      WHERE camera_id = $1
      RETURNING camera_id, name, location_label, location, rtsp_url AS stream_url, credentials_ref, enabled, created_at, updated_at
    `;
    const res = await this.pool.query(sql, [
      cameraId,
      dto.name,
      dto.location_label ?? null,
      dto.stream_url ?? null,
      dto.credentials_ref ?? null,
      dto.enabled ?? true,
    ]);
    return res.rows[0] ? this.mapRow(res.rows[0]) : null;
  }
}
