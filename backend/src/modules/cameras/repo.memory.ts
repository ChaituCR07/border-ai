import type { CamerasRepo, CameraFilters, CreateCameraDTO, UpdateCameraDTO } from './repo.js';
import type { CameraResource } from '../../types/domain.js';

export class InMemoryCamerasRepo implements CamerasRepo {
  private cameras = new Map<string, CameraResource>();

  constructor(private readonly mjpegBaseUrl: string) {}

  async list(filters: CameraFilters): Promise<CameraResource[]> {
    let list = Array.from(this.cameras.values());
    if (filters.enabled !== undefined) {
      list = list.filter(c => c.enabled === filters.enabled);
    }
    if (filters.q) {
      const q = filters.q.toLowerCase();
      list = list.filter(c =>
        (c.name && c.name.toLowerCase().includes(q)) ||
        (c.location_label && c.location_label.toLowerCase().includes(q)) ||
        c.camera_id.toLowerCase().includes(q)
      );
    }
    return list.sort((a, b) => a.camera_id.localeCompare(b.camera_id));
  }

  async getById(cameraId: string): Promise<CameraResource | null> {
    return this.cameras.get(cameraId) ?? null;
  }

  async create(dto: CreateCameraDTO): Promise<CameraResource> {
    const now = new Date().toISOString();
    const cam: CameraResource = {
      camera_id: dto.camera_id,
      name: dto.name,
      location_label: dto.location_label ?? null,
      stream_url: dto.stream_url ?? null,
      has_credentials: Boolean(dto.credentials_ref),
      credentials_ref: dto.credentials_ref ?? null,
      enabled: dto.enabled ?? true,
      live_view_url: `${this.mjpegBaseUrl.replace(/\/+$/, '')}/cam/${dto.camera_id}.mjpg`,
      created_at: now,
      updated_at: now,
    };
    this.cameras.set(dto.camera_id, cam);
    return cam;
  }

  async update(cameraId: string, dto: UpdateCameraDTO): Promise<CameraResource | null> {
    const existing = this.cameras.get(cameraId);
    if (!existing) return null;

    const updated: CameraResource = {
      ...existing,
      name: dto.name,
      location_label: dto.location_label ?? null,
      stream_url: dto.stream_url ?? null,
      has_credentials: Boolean(dto.credentials_ref),
      credentials_ref: dto.credentials_ref ?? null,
      enabled: dto.enabled ?? true,
      updated_at: new Date().toISOString(),
    };
    this.cameras.set(cameraId, updated);
    return updated;
  }
}
