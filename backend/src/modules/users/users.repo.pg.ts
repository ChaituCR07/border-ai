import pg from 'pg';
import { IUsersRepo } from './users.repo.js';
import { User, CreateUserData, UpdateUserData } from './users.types.js';

export class PgUsersRepo implements IUsersRepo {
  constructor(private pool: pg.Pool) {}

  private mapRow(row: any): User {
    let history: string[] = [];
    if (Array.isArray(row.password_history)) {
      history = row.password_history;
    } else if (typeof row.password_history === 'string') {
      try {
        history = JSON.parse(row.password_history);
      } catch {
        history = [];
      }
    }

    return {
      userId: row.user_id,
      username: row.username,
      email: row.email,
      displayName: row.display_name,
      role: row.role,
      passwordHash: row.password_hash,
      passwordHistory: history,
      status: row.status,
      mustChangePassword: row.must_change_password,
      tokenVersion: row.token_version,
      failedAttempts: row.failed_attempts,
      lastFailedAt: row.last_failed_at ? new Date(row.last_failed_at) : null,
      lastLoginAt: row.last_login_at ? new Date(row.last_login_at) : null,
      createdAt: new Date(row.created_at),
      createdBy: row.created_by,
      updatedAt: new Date(row.updated_at),
    };
  }

  async create(data: CreateUserData): Promise<User> {
    const q = `
      INSERT INTO users (
        username, email, display_name, role, password_hash, password_history,
        must_change_password, created_by
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *;
    `;
    const res = await this.pool.query(q, [
      data.username,
      data.email ?? null,
      data.displayName ?? null,
      data.role,
      data.passwordHash,
      JSON.stringify([data.passwordHash]),
      data.mustChangePassword ?? false,
      data.createdBy ?? null,
    ]);
    return this.mapRow(res.rows[0]);
  }

  async findById(userId: string): Promise<User | null> {
    const res = await this.pool.query('SELECT * FROM users WHERE user_id = $1;', [userId]);
    if (res.rows.length === 0) return null;
    return this.mapRow(res.rows[0]);
  }

  async findByUsername(username: string): Promise<User | null> {
    const res = await this.pool.query('SELECT * FROM users WHERE lower(username) = lower($1);', [username]);
    if (res.rows.length === 0) return null;
    return this.mapRow(res.rows[0]);
  }

  async list(): Promise<User[]> {
    const res = await this.pool.query('SELECT * FROM users ORDER BY created_at ASC;');
    return res.rows.map((r) => this.mapRow(r));
  }

  async update(userId: string, data: UpdateUserData): Promise<User | null> {
    const sets: string[] = ['updated_at = now()'];
    const values: any[] = [userId];
    let idx = 2;

    if (data.email !== undefined) {
      sets.push(`email = $${idx++}`);
      values.push(data.email);
    }
    if (data.displayName !== undefined) {
      sets.push(`display_name = $${idx++}`);
      values.push(data.displayName);
    }
    if (data.role !== undefined) {
      sets.push(`role = $${idx++}`);
      values.push(data.role);
    }
    if (data.status !== undefined) {
      sets.push(`status = $${idx++}`);
      values.push(data.status);
    }
    if (data.mustChangePassword !== undefined) {
      sets.push(`must_change_password = $${idx++}`);
      values.push(data.mustChangePassword);
    }
    if (data.passwordHash !== undefined) {
      sets.push(`password_hash = $${idx++}`);
      values.push(data.passwordHash);
    }
    if (data.passwordHistory !== undefined) {
      sets.push(`password_history = $${idx++}`);
      values.push(JSON.stringify(data.passwordHistory));
    }
    if (data.tokenVersion !== undefined) {
      sets.push(`token_version = $${idx++}`);
      values.push(data.tokenVersion);
    }
    if (data.failedAttempts !== undefined) {
      sets.push(`failed_attempts = $${idx++}`);
      values.push(data.failedAttempts);
    }
    if (data.lastFailedAt !== undefined) {
      sets.push(`last_failed_at = $${idx++}`);
      values.push(data.lastFailedAt);
    }
    if (data.lastLoginAt !== undefined) {
      sets.push(`last_login_at = $${idx++}`);
      values.push(data.lastLoginAt);
    }

    const q = `UPDATE users SET ${sets.join(', ')} WHERE user_id = $1 RETURNING *;`;
    const res = await this.pool.query(q, values);
    if (res.rows.length === 0) return null;
    return this.mapRow(res.rows[0]);
  }

  async delete(userId: string): Promise<boolean> {
    const res = await this.pool.query('DELETE FROM users WHERE user_id = $1;', [userId]);
    return (res.rowCount ?? 0) > 0;
  }

  async countActiveAdmins(): Promise<number> {
    const res = await this.pool.query(
      "SELECT count(*)::int as count FROM users WHERE role = 'ADMIN' AND status = 'ACTIVE';"
    );
    return res.rows[0]?.count ?? 0;
  }
}
