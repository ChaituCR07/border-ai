import type { WatchlistRepo, WatchlistFilters } from './repo.js';
import type { WatchlistResource, Actor } from '../../types/domain.js';
import type { AuditRepo } from '../../common/audit.js';
import { conflict, AppError } from '../../common/errors.js';
import { normalisePlate } from '../../common/plate.js';

export class WatchlistService {
  constructor(
    private readonly repo: WatchlistRepo,
    private readonly audit?: AuditRepo
  ) {}

  async list(filters: WatchlistFilters): Promise<WatchlistResource[]> {
    return this.repo.list(filters);
  }

  async create(body: any, actor: Actor, requestId?: string): Promise<WatchlistResource> {
    // Normalise identifier
    const normalized = body.entity_type === 'VEHICLE'
      ? normalisePlate(body.identifier)
      : body.identifier.trim().toLowerCase();

    // Check duplicate active
    const existing = await this.repo.findActiveByIdentifier(body.entity_type, normalized);
    if (existing) {
      throw conflict(`Active watchlist entry already exists for ${body.entity_type} '${body.identifier}'`);
    }

    const created = await this.repo.create({
      entity_type: body.entity_type,
      identifier: body.identifier.trim(),
      normalized_identifier: normalized,
      name: body.name.trim(),
      risk_level: body.risk_level,
      notes: body.notes?.trim() || null,
      consent_reference: body.consent_reference?.trim() || null,
    });

    if (this.audit) {
      await this.audit.record({
        actor: actor.id,
        action: 'WATCHLIST_CREATE',
        entity_type: 'WATCHLIST',
        entity_id: created.entity_id,
        request_id: requestId,
        detail: {
          entity_type: created.entity_type,
          identifier: created.identifier,
          risk_level: created.risk_level,
        },
      });
    }

    return created;
  }

  async delete(id: string, actor: Actor, requestId?: string): Promise<void> {
    const success = await this.repo.softDelete(id);
    if (success && this.audit) {
      await this.audit.record({
        actor: actor.id,
        action: 'WATCHLIST_DELETE',
        entity_type: 'WATCHLIST',
        entity_id: id,
        request_id: requestId,
      });
    }
  }
}
