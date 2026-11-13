import crypto from 'node:crypto';
import util from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const argon2Async = util.promisify(crypto.argon2);

export interface Argon2Params {
  memory: number;      // in KiB (e.g. 19456 = 19 MiB)
  passes: number;      // time cost
  parallelism: number; // lanes / threads
  tagLength: number;   // output length in bytes
}

export const OWASP_ARGON2_PARAMS: Argon2Params = {
  memory: 19456,
  passes: 2,
  parallelism: 1,
  tagLength: 32,
};

let activeParams: Argon2Params = { ...OWASP_ARGON2_PARAMS };

export function setArgon2Params(params: Partial<Argon2Params>): void {
  activeParams = { ...activeParams, ...params };
}

export function getArgon2Params(): Readonly<Argon2Params> {
  return activeParams;
}

// Semaphore to prevent Argon2 concurrency DoS
class HashSemaphore {
  private active = 0;
  private readonly max: number;
  private queue: Array<() => void> = [];

  constructor(max = 3) {
    this.max = max;
  }

  async acquire(): Promise<() => void> {
    if (this.active < this.max) {
      this.active++;
      return () => this.release();
    }

    return new Promise((resolve) => {
      this.queue.push(() => {
        this.active++;
        resolve(() => this.release());
      });
    });
  }

  private release() {
    this.active--;
    if (this.queue.length > 0 && this.active < this.max) {
      const next = this.queue.shift();
      if (next) next();
    }
  }

  get activeCount(): number {
    return this.active;
  }
}

const hashLimiter = new HashSemaphore(3);

function applyPepper(password: string): string {
  const pepper = process.env.PASSWORD_PEPPER;
  if (!pepper) return password;
  return crypto.createHmac('sha256', pepper).update(password).digest('base64');
}

/**
 * Hash a password using Argon2id with standard PHC string output
 */
export async function hashPassword(password: string): Promise<string> {
  const release = await hashLimiter.acquire();
  try {
    const normalized = applyPepper(password.normalize('NFKC'));
    const salt = crypto.randomBytes(16);
    const tag = await argon2Async('argon2id', {
      message: normalized,
      nonce: salt,
      memory: activeParams.memory,
      passes: activeParams.passes,
      parallelism: activeParams.parallelism,
      tagLength: activeParams.tagLength,
    });

    const saltB64 = salt.toString('base64').replace(/=/g, '');
    const tagB64 = tag.toString('base64').replace(/=/g, '');

    return `$argon2id$v=19$m=${activeParams.memory},t=${activeParams.passes},p=${activeParams.parallelism}$${saltB64}$${tagB64}`;
  } finally {
    release();
  }
}

/**
 * Verify a plaintext password against a stored PHC formatted Argon2 string
 */
export async function verifyPassword(storedPhc: string, password: string): Promise<boolean> {
  const release = await hashLimiter.acquire();
  try {
    const match = storedPhc.match(
      /^\$argon2(id|i|d)\$v=(\d+)\$m=(\d+),t=(\d+),p=(\d+)\$([A-Za-z0-9+/]+)\$([A-Za-z0-9+/]+)$/
    );
    if (!match) return false;

    const variant = match[1] as 'id' | 'i' | 'd';
    const memory = parseInt(match[3], 10);
    const passes = parseInt(match[4], 10);
    const parallelism = parseInt(match[5], 10);
    const salt = Buffer.from(match[6], 'base64');
    const expectedTag = Buffer.from(match[7], 'base64');

    const normalized = applyPepper(password.normalize('NFKC'));
    const computedTag = await argon2Async(`argon2${variant}`, {
      message: normalized,
      nonce: salt,
      memory,
      passes,
      parallelism,
      tagLength: expectedTag.length,
    });

    if (computedTag.length !== expectedTag.length) return false;
    return crypto.timingSafeEqual(computedTag, expectedTag);
  } catch {
    return false;
  } finally {
    release();
  }
}

let DUMMY_HASH: string | null = null;

export async function initDummy(): Promise<void> {
  if (!DUMMY_HASH) {
    DUMMY_HASH = await hashPassword('dummy-salt-for-constant-timing-defense-string');
  }
}

/**
 * Constant-time password verification preventing username enumeration
 */
export async function verifyOrDummy(storedPhc: string | undefined, password: string): Promise<boolean> {
  if (!DUMMY_HASH) {
    await initDummy();
  }

  if (storedPhc) {
    return verifyPassword(storedPhc, password);
  }

  await verifyPassword(DUMMY_HASH!, password);
  return false;
}

/**
 * Determine if stored hash parameters need to be upgraded to current baseline
 */
export function needsRehash(storedPhc: string): boolean {
  const match = storedPhc.match(/\$argon2id\$v=\d+\$m=(\d+),t=(\d+),p=(\d+)\$/);
  if (!match) return true;
  const m = parseInt(match[1], 10);
  const t = parseInt(match[2], 10);
  const p = parseInt(match[3], 10);

  return m < activeParams.memory || t < activeParams.passes || p < activeParams.parallelism;
}

// Load common passwords blacklist once
let commonPasswords: Set<string> | null = null;

function loadCommonPasswords(): Set<string> {
  if (!commonPasswords) {
    try {
      const dirname = path.dirname(fileURLToPath(import.meta.url));
      const filePath = path.join(dirname, 'common-passwords.txt');
      if (fs.existsSync(filePath)) {
        const lines = fs.readFileSync(filePath, 'utf-8').split(/\r?\n/);
        commonPasswords = new Set(lines.map((l) => l.trim().toLowerCase()).filter(Boolean));
      } else {
        commonPasswords = new Set();
      }
    } catch {
      commonPasswords = new Set();
    }
  }
  return commonPasswords;
}

export interface PasswordValidationContext {
  username?: string;
  email?: string;
  history?: string[];
}

export interface PasswordValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validate password against NIST SP 800-63B standards and organizational rules
 */
export async function validatePassword(
  password: string,
  context: PasswordValidationContext = {}
): Promise<PasswordValidationResult> {
  const errors: string[] = [];
  const normalized = password.normalize('NFKC');

  // 1. Length requirements (12 to 128 code points)
  const length = Array.from(normalized).length;
  if (length < 12) {
    errors.push('PASSWORD_TOO_SHORT');
  } else if (length > 128) {
    errors.push('PASSWORD_TOO_LONG');
  }

  // 2. Common password list check
  const blacklist = loadCommonPasswords();
  if (blacklist.has(normalized.toLowerCase())) {
    errors.push('PASSWORD_COMMONLY_USED');
  }

  // 3. Username / email resemblance check
  if (context.username && context.username.trim().length >= 3) {
    const u = context.username.trim().toLowerCase();
    if (normalized.toLowerCase().includes(u)) {
      errors.push('PASSWORD_CONTAINS_USERNAME');
    }
  }

  if (context.email && context.email.includes('@')) {
    const local = context.email.split('@')[0].toLowerCase();
    if (local.length >= 3 && normalized.toLowerCase().includes(local)) {
      errors.push('PASSWORD_CONTAINS_EMAIL');
    }
  }

  // 4. History check (last N hashes)
  if (context.history && context.history.length > 0) {
    for (const priorHash of context.history.slice(0, 5)) {
      const match = await verifyPassword(priorHash, password);
      if (match) {
        errors.push('PASSWORD_IN_HISTORY');
        break;
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
