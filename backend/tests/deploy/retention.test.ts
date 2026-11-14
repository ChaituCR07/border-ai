import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { runRetentionCycle } from '../../scripts/retention-loop.js';

describe('Data Retention Service', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'retention-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('scans and unlinks expired snapshots while keeping fresh snapshots intact', async () => {
    // 1. Create a fresh file (1 hour old)
    const freshFile = path.join(tmpDir, 'fresh_evidence.jpg');
    fs.writeFileSync(freshFile, 'fresh data');

    // 2. Create an expired file (20 days old)
    const expiredFile = path.join(tmpDir, 'old_evidence.jpg');
    fs.writeFileSync(expiredFile, 'expired data');
    const pastTime = (Date.now() - 20 * 86400 * 1000) / 1000;
    fs.utimesSync(expiredFile, pastTime, pastTime);

    // Mock PG pool
    const mockPool = {
      connect: async () => ({
        query: async () => ({ rowCount: 0 }),
        release: () => {},
      }),
    } as any;

    const result = await runRetentionCycle(mockPool, tmpDir, {
      eventsDays: 30,
      snapshotsDays: 14,
      auditDays: 365,
    });

    expect(result.purgedSnapshots).toBe(1);
    expect(fs.existsSync(freshFile)).toBe(true);
    expect(fs.existsSync(expiredFile)).toBe(false);
  });

  it('does not unlink files in dryRun mode', async () => {
    const expiredFile = path.join(tmpDir, 'old_dryrun.jpg');
    fs.writeFileSync(expiredFile, 'expired data');
    const pastTime = (Date.now() - 25 * 86400 * 1000) / 1000;
    fs.utimesSync(expiredFile, pastTime, pastTime);

    const mockPool = {
      connect: async () => ({
        query: async () => ({ rowCount: 0 }),
        release: () => {},
      }),
    } as any;

    const result = await runRetentionCycle(mockPool, tmpDir, {
      eventsDays: 30,
      snapshotsDays: 14,
      auditDays: 365,
      dryRun: true,
    });

    expect(result.purgedSnapshots).toBe(1);
    expect(fs.existsSync(expiredFile)).toBe(true);
  });
});
