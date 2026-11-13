import { describe, it, expect, beforeAll } from 'vitest';
import {
  hashPassword,
  verifyPassword,
  verifyOrDummy,
  needsRehash,
  validatePassword,
  initDummy,
  setArgon2Params,
  OWASP_ARGON2_PARAMS,
} from '../../src/security/passwords.js';

describe('Argon2id Passwords & Policy', () => {
  beforeAll(async () => {
    // Fast parameters for test execution
    setArgon2Params({ memory: 4096, passes: 1, parallelism: 1, tagLength: 32 });
    await initDummy();
  });

  it('hashes and verifies a password correctly', async () => {
    const raw = 'CorrectHorseBatteryStaple123!';
    const phc = await hashPassword(raw);

    expect(phc).toMatch(/^\$argon2id\$v=19\$m=\d+,t=\d+,p=\d+\$[A-Za-z0-9+/]+\$[A-Za-z0-9+/]+$/);
    const valid = await verifyPassword(phc, raw);
    expect(valid).toBe(true);

    const invalid = await verifyPassword(phc, 'WrongPassword123!');
    expect(invalid).toBe(false);
  });

  it('handles dummy hash verification without user enumeration leak', async () => {
    const valid = await verifyOrDummy(undefined, 'AnyPassword123!');
    expect(valid).toBe(false);
  });

  it('detects when hash parameters are below current baseline', async () => {
    const weakPhc = '$argon2id$v=19$m=2048,t=1,p=1$c2FsdHNhbHQ$dGFndGFn';
    expect(needsRehash(weakPhc)).toBe(true);

    // Current test baseline is m=4096, t=1, p=1
    const currentPhc = await hashPassword('Sample123456789!');
    expect(needsRehash(currentPhc)).toBe(false);
  });

  it('enforces password policy requirements (length, common passwords, username/email resemblance)', async () => {
    // Too short
    const shortRes = await validatePassword('short');
    expect(shortRes.valid).toBe(false);
    expect(shortRes.errors).toContain('PASSWORD_TOO_SHORT');

    // Common password
    const commonRes = await validatePassword('password12345');
    expect(commonRes.valid).toBe(false);
    expect(commonRes.errors).toContain('PASSWORD_COMMONLY_USED');

    // Resemblance to username
    const userRes = await validatePassword('MyJohnDoeSecret123', { username: 'JohnDoe' });
    expect(userRes.valid).toBe(false);
    expect(userRes.errors).toContain('PASSWORD_CONTAINS_USERNAME');

    // Resemblance to email
    const emailRes = await validatePassword('SecretAgentSmith123', { email: 'agentSmith@border.gov' });
    expect(emailRes.valid).toBe(false);
    expect(emailRes.errors).toContain('PASSWORD_CONTAINS_EMAIL');

    // Valid compliant password
    const goodRes = await validatePassword('BorderPatrolShield2026!#');
    expect(goodRes.valid).toBe(true);
    expect(goodRes.errors).toHaveLength(0);
  });

  it('rejects passwords present in historical password hashes', async () => {
    const oldPassword = 'OldSecurePassword123!';
    const oldHash = await hashPassword(oldPassword);

    const res = await validatePassword(oldPassword, { history: [oldHash] });
    expect(res.valid).toBe(false);
    expect(res.errors).toContain('PASSWORD_IN_HISTORY');
  });
});
