import crypto from 'node:crypto';
import pg from 'pg';
import dotenv from 'dotenv';
import { hashPassword, validatePassword } from '../src/security/passwords.js';
import { Role } from '../src/security/policy.js';

dotenv.config();

const { Pool } = pg;

function parseArgs(): { username?: string; role?: Role; password?: string; email?: string } {
  const args = process.argv.slice(2);
  const result: any = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--username' && args[i + 1]) result.username = args[++i];
    if (args[i] === '--role' && args[i + 1]) result.role = args[++i].toUpperCase();
    if (args[i] === '--password' && args[i + 1]) result.password = args[++i];
    if (args[i] === '--email' && args[i + 1]) result.email = args[++i];
  }
  return result;
}

async function run() {
  const parsed = parseArgs();
  const username = parsed.username || `user_${crypto.randomBytes(4).toString('hex')}`;
  const role: Role = (parsed.role as Role) || 'OPERATOR';
  const email = parsed.email || `${username}@border.internal`;
  const isGeneratedPw = !parsed.password;
  const password =
    parsed.password || `DemoPass!_${crypto.randomBytes(8).toString('base64url')}2026`;

  console.log(`=== Border-AI User Creation CLI ===`);
  console.log(`Target: ${username} (Role: ${role})`);

  const validRoles: Role[] = ['ADMIN', 'OPERATOR', 'INVESTIGATOR', 'VIEWER'];
  if (!validRoles.includes(role)) {
    console.error(`Invalid role: ${role}. Must be one of: ${validRoles.join(', ')}`);
    process.exit(1);
  }

  const policy = await validatePassword(password, { username, email });
  if (!policy.valid) {
    console.error(`Password policy error: ${policy.errors.join(', ')}`);
    process.exit(1);
  }

  const pool = new Pool({
    connectionString:
      process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/border_ai',
  });

  try {
    const client = await pool.connect();
    try {
      const passwordHash = await hashPassword(password);
      const q = `
        INSERT INTO users (username, email, role, password_hash, password_history, status, must_change_password)
        VALUES ($1, $2, $3, $4, $5, 'ACTIVE', $6)
        RETURNING user_id, username, role, must_change_password;
      `;

      const res = await client.query(q, [
        username,
        email,
        role,
        passwordHash,
        JSON.stringify([passwordHash]),
        isGeneratedPw,
      ]);

      const u = res.rows[0];
      console.log(`SUCCESS: User created successfully!`);
      console.log(`User ID:               ${u.user_id}`);
      console.log(`Username:              ${u.username}`);
      console.log(`Role:                  ${u.role}`);
      if (isGeneratedPw) {
        console.log(`One-time Password:     ${password}`);
        console.log(`(User must change password on first login)`);
      }
    } finally {
      client.release();
    }
  } catch (err: any) {
    console.error(`Failed to create user: ${err.message}`);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  run();
}
