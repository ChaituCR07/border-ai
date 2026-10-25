import type pg from 'pg';
import type { WatchlistRepo, WatchlistFilters, CreateWatchlistDTO } from './repo.js';
import type { WatchlistResource } from '../../types/domain.js';
import { pgTsToIso } from '../../common/time.js';

export class PgWatchlistRepo implements WatchlistRepo {
  constructor(private readonly pool: pg.Pool) {}

  private mapRow(r: any): WatchlistResource {
    return {
      entity_id: r.entity_id,
      entity_type: r.entity_type,
      identifier: r.identifier,
      name: r.name,
      risk_level: r.risk_level,
      notes: r.notes ?? r.description ?? null,
      consent_reference: r.consent_reference ?? null,
      active: r.active ?? (r.deleted_at === null),
      created_at: pgTsToIso(r.created_at) ?? r.created_at,
      updated_at: pgTsToIso(r.updated_at) ?? r.updated_at ?? r.created_at,
    };
  }

  async list(filters: WatchlistFilters): Promise<WatchlistResource[]> {
    const where: string[] = [];
    const args: any[] = [];
    let idx = 1;

    if (!filters.includeDeleted) {
      where.push('deleted_at IS NULL AND active = true');
    }
    if (filters.entityType) {
      where.push(`entity_type = $${idx++}`);
      args.push(filters.entityType);
    }
    if (filters.riskLevel) {
      where.push(`risk_level = $${idx++}`);
      args.push(filters.riskLevel);
    }
    if (filters.q) {
      where.push(`(name ILIKE $${idx} OR identifier ILIKE $${idx} OR normalized_identifier ILIKE $${idx})`);
      args.push(`%${filters.q}%`);
      idx++;
    }

    const whereClause = where.length > 0 ? `WHERE ${where.join(' AND ')}` : '';
    const sql = `
      SELECT entity_id, entity_type, identifier, normalized_identifier, name, risk_level,
             notes, consent_reference, active, deleted_at, created_at, updated_at
      FROM watchlist
      ${whereClause}
      ORDER BY created_at DESC
    `;

    const res = await this.pool.query(sql, args);
    return res.rows.map(r => this.mapRow(r));
  }

  async getById(id: string): Promise<WatchlistResource | null> {
    const sql = `
      SELECT entity_id, entity_type, identifier, normalized_identifier, name, risk_level,
             notes, consent_reference, active, deleted_at, created_at, updated_at
      FROM watchlist
      WHERE entity_id = $1::uuid
    `;
    const res = await this.pool.query(sql, [id]);
    return res.rows[0] ? this.mapRow(res.rows[0]) : null;
  }

  async findActiveByIdentifier(entityType: string, normalizedIdentifier: string): Promise<WatchlistResource | null> {
    const sql = `
      SELECT entity_id, entity_type, identifier, normalized_identifier, name, risk_level,
             notes, consent_reference, active, deleted_at, created_at, updated_at
      FROM watchlist
      WHERE entity_type = $1 AND normalized_identifier = $2 AND deleted_at IS NULL AND active = true
      LIMIT 1
    `;
    const res = await this.pool.query(sql, [entityType, normalizedIdentifier]);
    return res.rows[0] ? this.mapRow(res.rows[0]) : null;
  }

  async create(dto: CreateWatchlistDTO): Promise<WatchlistResource> {
    const sql = `
      INSERT INTO watchlist (
        entity_type, identifier, normalized_identifier, name, risk_level, notes, consent_reference, active, updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, true, now())
      RETURNING entity_id, entity_type, identifier, normalized_identifier, name, risk_level,
                notes, consent_reference, active, deleted_at, created_at, updated_at
    `;
    const res = await this.pool.query(sql, [
      dto.entity_type,
      dto.identifier,
      dto.normalized_identifier,
      dto.name,
      dto.risk_level,
      dto.notes ?? null,
      dto.consent_reference ?? null,
    ]);
    return this.mapRow(res.rows[0]);
  }

  async softDelete(id: string): Promise<boolean> {
    const sql = `
      UPDATE watchlist
      SET active = false, deleted_at = now(), updated_at = now()
      WHERE entity_id = $1::uuid AND deleted_at IS NULL
      RETURNING entity_id
    `;
    const res = await this.pool.query(sql, [id]);
    return (res.rowCount ?? 0) > 0;
  }
}
