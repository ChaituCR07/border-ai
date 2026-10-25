import type { CameraResource } from '../../types/domain.js';

export interface CameraFilters {
  enabled?: boolean;
  q?: string;
}

export interface CreateCameraDTO {
  camera_id: string;
  name: string;
  location_label?: string | null;
  stream_url?: string | null;
  credentials_ref?: string | null;
  enabled?: boolean;
}

export interface UpdateCameraDTO {
  name: string;
  location_label?: string | null;
  stream_url?: string | null;
  credentials_ref?: string | null;
  enabled?: boolean;
}

export interface CamerasRepo {
  list(filters: CameraFilters): Promise<CameraResource[]>;
  getById(cameraId: string): Promise<CameraResource | null>;
  create(dto: CreateCameraDTO): Promise<CameraResource>;
  update(cameraId: string, dto: UpdateCameraDTO): Promise<CameraResource | null>;
}
