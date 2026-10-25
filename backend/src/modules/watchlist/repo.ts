import type { WatchlistResource, WatchlistEntityType, WatchlistRiskLevel } from '../../types/domain.js';

export interface WatchlistFilters {
  entityType?: WatchlistEntityType;
  riskLevel?: WatchlistRiskLevel;
  q?: string;
  includeDeleted?: boolean;
}

export interface CreateWatchlistDTO {
  entity_type: WatchlistEntityType;
  identifier: string;
  normalized_identifier: string;
  name: string;
  risk_level: WatchlistRiskLevel;
  notes?: string | null;
  consent_reference?: string | null;
}

export interface WatchlistRepo {
  list(filters: WatchlistFilters): Promise<WatchlistResource[]>;
  getById(id: string): Promise<WatchlistResource | null>;
  findActiveByIdentifier(entityType: WatchlistEntityType, normalizedIdentifier: string): Promise<WatchlistResource | null>;
  create(dto: CreateWatchlistDTO): Promise<WatchlistResource>;
  softDelete(id: string): Promise<boolean>;
}
