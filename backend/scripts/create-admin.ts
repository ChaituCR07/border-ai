import fs from 'node:fs';
import readline from 'node:readline/promises';
import pg from 'pg';
import dotenv from 'dotenv';
import { hashPassword, validatePassword } from '../src/security/passwords.js';

dotenv.config();

const { Pool } = pg;

async function promptInput(query: string, hide = false): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  try {
    if (!hide) {
      return (await rl.question(query)).trim();
    }
    // Simple prompt
    const answer = await rl.question(query);
    return answer.trim();
  } finally {
    rl.close();
  }
}

async function run() {
  console.log('=== Border-AI First-Admin Bootstrap CLI ===');

  const pool = new Pool({
    connectionString:
      process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/border_ai',
  });

  const force = process.argv.includes('--force');

  try {
    const client = await pool.connect();
    try {
      // 1. Check for existing active administrators
      const countRes = await client.query(
        "SELECT count(*)::int as count FROM users WHERE role = 'ADMIN' AND status = 'ACTIVE';"
      );
      const existingAdmins = countRes.rows[0]?.count ?? 0;

      if (existingAdmins > 0 && !force) {
        console.error(
          `[bootstrap] ERROR: ${existingAdmins} active administrator(s) already exist. Use --force to proceed anyway.`
        );
        process.exit(1);
      }

      // 2. Obtain username and password (from env or CLI)
      let username = process.env.BOOTSTRAP_ADMIN_USER;
      let password = process.env.BOOTSTRAP_ADMIN_PASSWORD;

      if (!password && process.env.BOOTSTRAP_ADMIN_PASSWORD_FILE) {
        if (fs.existsSync(process.env.BOOTSTRAP_ADMIN_PASSWORD_FILE)) {
          password = fs.readFileSync(process.env.BOOTSTRAP_ADMIN_PASSWORD_FILE, 'utf-8').trim();
        }
      }

      if (!username) {
        username = await promptInput('Enter Admin Username (default: admin): ');
        if (!username) username = 'admin';
      }

      if (!password) {
        password = await promptInput('Enter Admin Password (min 12 chars): ', true);
      }

      // 3. Validate against password policy
      const policy = await validatePassword(password, { username });
      if (!policy.valid) {
        console.error(`[bootstrap] Password policy violation: ${policy.errors.join(', ')}`);
        process.exit(1);
      }

      // 4. Hash password with Argon2id
      console.log('[bootstrap] Hashing password with Argon2id...');
      const passwordHash = await hashPassword(password);

      // 5. Insert into users table
      const q = `
        INSERT INTO users (username, role, password_hash, password_history, status, must_change_password)
        VALUES ($1, 'ADMIN', $2, $3, 'ACTIVE', false)
        ON CONFLICT (lower(username)) DO UPDATE
          SET role = 'ADMIN', password_hash = $2, password_history = $3, status = 'ACTIVE'
        RETURNING user_id, username, role;
      `;

      const insertRes = await client.query(q, [
        username,
        passwordHash,
        JSON.stringify([passwordHash]),
      ]);

      const created = insertRes.rows[0];
      console.log(
        `[bootstrap] SUCCESS: Administrator account '${created.username}' (ID: ${created.user_id}) created.`
      );
    } finally {
      client.release();
    }
  } catch (err: any) {
    console.error(`[bootstrap] Fatal error: ${err.message}`);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// Only execute when run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  run();
}
