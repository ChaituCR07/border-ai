import { randomUUID } from 'node:crypto';
import type { WatchlistRepo, WatchlistFilters, CreateWatchlistDTO } from './repo.js';
import type { WatchlistResource } from '../../types/domain.js';

interface MemoryWatchlistEntry extends WatchlistResource {
  normalized_identifier: string;
  deleted_at: string | null;
}

export class InMemoryWatchlistRepo implements WatchlistRepo {
  private items: MemoryWatchlistEntry[] = [];

  async list(filters: WatchlistFilters): Promise<WatchlistResource[]> {
    let list = [...this.items];

    if (!filters.includeDeleted) {
      list = list.filter(i => i.active && !i.deleted_at);
    }
    if (filters.entityType) {
      list = list.filter(i => i.entity_type === filters.entityType);
    }
    if (filters.riskLevel) {
      list = list.filter(i => i.risk_level === filters.riskLevel);
    }
    if (filters.q) {
      const q = filters.q.toLowerCase();
      list = list.filter(i =>
        i.name.toLowerCase().includes(q) ||
        i.identifier.toLowerCase().includes(q) ||
        i.normalized_identifier.toLowerCase().includes(q)
      );
    }

    return list.sort((a, b) => b.created_at.localeCompare(a.created_at));
  }

  async getById(id: string): Promise<WatchlistResource | null> {
    return this.items.find(i => i.entity_id === id) ?? null;
  }

  async findActiveByIdentifier(entityType: string, normalizedIdentifier: string): Promise<WatchlistResource | null> {
    return this.items.find(i =>
      i.entity_type === entityType &&
      i.normalized_identifier === normalizedIdentifier &&
      i.active &&
      !i.deleted_at
    ) ?? null;
  }

  async create(dto: CreateWatchlistDTO): Promise<WatchlistResource> {
    const now = new Date().toISOString();
    const entry: MemoryWatchlistEntry = {
      entity_id: randomUUID(),
      entity_type: dto.entity_type,
      identifier: dto.identifier,
      normalized_identifier: dto.normalized_identifier,
      name: dto.name,
      risk_level: dto.risk_level,
      notes: dto.notes ?? null,
      consent_reference: dto.consent_reference ?? null,
      active: true,
      deleted_at: null,
      created_at: now,
      updated_at: now,
    };
    this.items.push(entry);
    return entry;
  }

  async softDelete(id: string): Promise<boolean> {
    const item = this.items.find(i => i.entity_id === id && i.active);
    if (!item) return false;
    item.active = false;
    item.deleted_at = new Date().toISOString();
    item.updated_at = new Date().toISOString();
    return true;
  }
}
