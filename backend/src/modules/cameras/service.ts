import type { CamerasRepo, CameraFilters, CreateCameraDTO, UpdateCameraDTO } from './repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { conflict, notFound, AppError } from '../../common/errors.js';
import type { CameraResource, Actor } from '../../types/domain.js';

export class CamerasService {
  constructor(
    private readonly repo: CamerasRepo,
    private readonly audit?: AuditRepo
  ) {}

  async list(filters: CameraFilters): Promise<CameraResource[]> {
    return this.repo.list(filters);
  }

  async get(id: string): Promise<CameraResource> {
    const cam = await this.repo.getById(id);
    if (!cam) throw notFound(`Camera '${id}'`);
    return cam;
  }

  async create(dto: CreateCameraDTO, actor: Actor, requestId?: string): Promise<CameraResource> {
    const existing = await this.repo.getById(dto.camera_id);
    if (existing) {
      throw conflict(`Camera '${dto.camera_id}' already exists`);
    }

    try {
      const created = await this.repo.create(dto);
      if (this.audit) {
        await this.audit.record({
          actor: actor.id,
          action: 'CAMERA_CREATE',
          entity_type: 'CAMERA',
          entity_id: created.camera_id,
          request_id: requestId,
          detail: { name: created.name, enabled: created.enabled },
        });
      }
      return created;
    } catch (err: any) {
      if (err.code === '23505') {
        throw conflict(`Camera '${dto.camera_id}' already exists`);
      }
      throw err;
    }
  }

  async update(id: string, dto: UpdateCameraDTO, actor: Actor, requestId?: string): Promise<CameraResource> {
    const updated = await this.repo.update(id, dto);
    if (!updated) throw notFound(`Camera '${id}'`);

    if (this.audit) {
      await this.audit.record({
        actor: actor.id,
        action: 'CAMERA_UPDATE',
        entity_type: 'CAMERA',
        entity_id: id,
        request_id: requestId,
        detail: { name: updated.name, enabled: updated.enabled },
      });
    }

    return updated;
  }
}
