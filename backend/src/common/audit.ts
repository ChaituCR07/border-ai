import type pg from 'pg';

export interface AuditLogEntry {
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  request_id?: string;
  detail?: Record<string, unknown>;
}

export interface AuditRepo {
  record(entry: AuditLogEntry): Promise<void>;
  list(limit?: number): Promise<AuditLogEntry[]>;
}

export class PgAuditRepo implements AuditRepo {
  constructor(private readonly pool: pg.Pool) {}

  async record(entry: AuditLogEntry): Promise<void> {
    const sql = `
      INSERT INTO api_audit_log (actor, action, entity_type, entity_id, request_id, detail)
      VALUES ($1, $2, $3, $4, $5, $6)
    `;
    await this.pool.query(sql, [
      entry.actor,
      entry.action,
      entry.entity_type,
      entry.entity_id,
      entry.request_id || null,
      JSON.stringify(entry.detail || {}),
    ]);
  }

  async list(limit = 50): Promise<AuditLogEntry[]> {
    const res = await this.pool.query(
      'SELECT actor, action, entity_type, entity_id, request_id, detail FROM api_audit_log ORDER BY audit_id DESC LIMIT $1',
      [limit]
    );
    return res.rows;
  }
}

export class InMemoryAuditRepo implements AuditRepo {
  private readonly records: AuditLogEntry[] = [];

  async record(entry: AuditLogEntry): Promise<void> {
    this.records.unshift(entry);
  }

  async list(limit = 50): Promise<AuditLogEntry[]> {
    return this.records.slice(0, limit);
  }
}
