import crypto from 'node:crypto';
import type pg from 'pg';
import type { AuditLogEntry, AuditRepo } from '../common/audit.js';

export const GENESIS_HASH = '0000000000000000000000000000000000000000000000000000000000000000';

export interface AuditRecord extends AuditLogEntry {
  audit_id?: number | string;
  at: string;
  role?: string;
  ip?: string;
  user_agent_hash?: string;
  prev_hash: string;
  hash: string;
}

export interface AuditHashParams {
  prevHash: string;
  timestamp: string;
  actor: string;
  action: string;
  entityType: string;
  entityId: string;
  detail?: unknown;
}

/**
 * Deterministic JSON serialization:
 * - Recursively sorts object keys lexicographically
 * - No whitespace
 * - Deterministic representation of null, booleans, and numbers
 */
export function canonicalJson(val: unknown): string {
  if (val === null || val === undefined) {
    return 'null';
  }
  if (typeof val === 'number' || typeof val === 'boolean' || typeof val === 'string') {
    return JSON.stringify(val);
  }
  if (Array.isArray(val)) {
    return '[' + val.map(canonicalJson).join(',') + ']';
  }
  if (typeof val === 'object') {
    const keys = Object.keys(val as Record<string, unknown>).sort();
    const parts = keys.map((k) => `${JSON.stringify(k)}:${canonicalJson((val as Record<string, unknown>)[k])}`);
    return '{' + parts.join(',') + '}';
  }
  return JSON.stringify(val);
}

/**
 * Calculates SHA-256 hash for audit record:
 * SHA-256 over `${prev_hash}:${timestamp}:${actor_id}:${action}:${target_type}:${target_id}:${canonical_payload}`
 */
export function computeAuditHash(params: AuditHashParams): string {
  const canonicalPayload = canonicalJson(params.detail ?? {});
  const message = `${params.prevHash}:${params.timestamp}:${params.actor}:${params.action}:${params.entityType}:${params.entityId}:${canonicalPayload}`;
  return crypto.createHash('sha256').update(message, 'utf8').digest('hex');
}

export interface AuditVerificationResult {
  valid: boolean;
  totalVerified: number;
  brokenAt?: number;
  expectedHash?: string;
  actualHash?: string;
  reason?: string;
}

/**
 * Verifies sequential hash integrity of an array of audit records
 */
export function verifyAuditChain(records: AuditRecord[]): AuditVerificationResult {
  if (records.length === 0) {
    return { valid: true, totalVerified: 0 };
  }

  let expectedPrevHash = GENESIS_HASH;

  for (let i = 0; i < records.length; i++) {
    const rec = records[i]!;
    const seq = rec.audit_id !== undefined ? Number(rec.audit_id) : i + 1;

    // Check prev_hash links to prior hash
    if (i === 0) {
      if (rec.prev_hash !== GENESIS_HASH) {
        return {
          valid: false,
          totalVerified: i,
          brokenAt: seq,
          expectedHash: GENESIS_HASH,
          actualHash: rec.prev_hash,
          reason: `Genesis record does not link to GENESIS_HASH`,
        };
      }
    } else {
      if (rec.prev_hash !== expectedPrevHash) {
        return {
          valid: false,
          totalVerified: i,
          brokenAt: seq,
          expectedHash: expectedPrevHash,
          actualHash: rec.prev_hash,
          reason: `prev_hash mismatch with previous record's hash`,
        };
      }
    }

    // Verify hash calculation
    const calculatedHash = computeAuditHash({
      prevHash: rec.prev_hash,
      timestamp: rec.at,
      actor: rec.actor,
      action: rec.action,
      entityType: rec.entity_type,
      entityId: rec.entity_id,
      detail: rec.detail,
    });

    if (calculatedHash !== rec.hash) {
      return {
        valid: false,
        totalVerified: i,
        brokenAt: seq,
        expectedHash: calculatedHash,
        actualHash: rec.hash,
        reason: `Hash calculation mismatch (data tampered or hash altered)`,
      };
    }

    expectedPrevHash = rec.hash;
  }

  return {
    valid: true,
    totalVerified: records.length,
  };
}

/**
 * In-memory chained audit log implementation for testing and development
 */
export class InMemoryChainedAuditRepo implements AuditRepo {
  private chain: AuditRecord[] = [];
  private currentHead: string = GENESIS_HASH;

  async record(
    entry: AuditLogEntry,
    meta?: { role?: string; ip?: string; user_agent_hash?: string; timestamp?: string }
  ): Promise<AuditRecord> {
    const timestamp = meta?.timestamp ?? new Date().toISOString();
    const prevHash = this.currentHead;

    const hash = computeAuditHash({
      prevHash,
      timestamp,
      actor: entry.actor,
      action: entry.action,
      entityType: entry.entity_type,
      entityId: entry.entity_id,
      detail: entry.detail,
    });

    const record: AuditRecord = {
      ...entry,
      audit_id: this.chain.length + 1,
      at: timestamp,
      role: meta?.role,
      ip: meta?.ip,
      user_agent_hash: meta?.user_agent_hash,
      prev_hash: prevHash,
      hash,
    };

    this.chain.push(record);
    this.currentHead = hash;
    return record;
  }

  async list(limit = 50): Promise<AuditRecord[]> {
    return [...this.chain].reverse().slice(0, limit);
  }

  getAllRecords(): AuditRecord[] {
    return [...this.chain];
  }

  getHead(): string {
    return this.currentHead;
  }

  // Intentionally tamper with a record to test fraud detection
  tamperRecord(index: number, modifiedDetail: Record<string, unknown>): void {
    if (this.chain[index]) {
      this.chain[index] = {
        ...this.chain[index]!,
        detail: modifiedDetail,
      };
    }
  }
}

/**
 * PostgreSQL chained audit log implementation with atomic audit_head locking
 */
export class PgChainedAuditRepo implements AuditRepo {
  constructor(private readonly pool: pg.Pool) {}

  async record(
    entry: AuditLogEntry,
    meta?: { role?: string; ip?: string; user_agent_hash?: string; timestamp?: string }
  ): Promise<AuditRecord> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      // 1. Lock audit_head to ensure sequential chaining without race conditions
      const headRes = await client.query('SELECT hash FROM audit_head WHERE head_id = 1 FOR UPDATE');
      const prevHash = headRes.rows[0]?.hash || GENESIS_HASH;
      const timestamp = meta?.timestamp ?? new Date().toISOString();

      // 2. Compute SHA-256 hash
      const hash = computeAuditHash({
        prevHash,
        timestamp,
        actor: entry.actor,
        action: entry.action,
        entityType: entry.entity_type,
        entityId: entry.entity_id,
        detail: entry.detail,
      });

      // 3. Insert record into api_audit_log
      const insertSql = `
        INSERT INTO api_audit_log (
          at, actor, action, entity_type, entity_id, request_id,
          role, ip, user_agent_hash, prev_hash, hash, detail
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING audit_id
      `;

      const insertRes = await client.query(insertSql, [
        timestamp,
        entry.actor,
        entry.action,
        entry.entity_type,
        entry.entity_id,
        entry.request_id || null,
        meta?.role || null,
        meta?.ip || null,
        meta?.user_agent_hash || null,
        prevHash,
        hash,
        JSON.stringify(entry.detail || {}),
      ]);

      // 4. Update audit_head tip
      await client.query(
        'UPDATE audit_head SET hash = $1, updated_at = now() WHERE head_id = 1',
        [hash]
      );

      await client.query('COMMIT');

      return {
        ...entry,
        audit_id: insertRes.rows[0]?.audit_id,
        at: timestamp,
        role: meta?.role,
        ip: meta?.ip,
        user_agent_hash: meta?.user_agent_hash,
        prev_hash: prevHash,
        hash,
      };
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  async list(limit = 50): Promise<AuditRecord[]> {
    const res = await this.pool.query(
      `SELECT audit_id, at, actor, action, entity_type, entity_id, request_id,
              role, ip, user_agent_hash, prev_hash, hash, detail
       FROM api_audit_log
       ORDER BY audit_id DESC
       LIMIT $1`,
      [limit]
    );
    return res.rows.map((row) => ({
      ...row,
      at: new Date(row.at).toISOString(),
    }));
  }

  async fetchAllAscending(): Promise<AuditRecord[]> {
    const res = await this.pool.query(
      `SELECT audit_id, at, actor, action, entity_type, entity_id, request_id,
              role, ip, user_agent_hash, prev_hash, hash, detail
       FROM api_audit_log
       ORDER BY audit_id ASC`
    );
    return res.rows.map((row) => ({
      ...row,
      at: new Date(row.at).toISOString(),
    }));
  }
}
