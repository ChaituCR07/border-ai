import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import sharp from 'sharp';
import {
  processSnapshot,
  resolveSafeSnapshotPath,
} from '../../src/modules/notifications/snapshot.js';

describe('Snapshot Downscaling, EXIF Stripping & Privacy Rules', () => {
  let tempDir: string;
  let sampleJpgPath: string;

  beforeAll(async () => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'snap-test-'));
    sampleJpgPath = path.join(tempDir, 'sample.jpg');

    // Create a 1920x1080 test image with metadata
    await sharp({
      create: {
        width: 1920,
        height: 1080,
        channels: 3,
        background: { r: 20, g: 80, b: 160 },
      },
    })
      .jpeg()
      .toFile(sampleJpgPath);
  });

  afterAll(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  it('downscales high-resolution images to max 640px and strips metadata', async () => {
    const res = await processSnapshot('sample.jpg', {
      rootDir: tempDir,
      personRelated: false,
    });

    expect(res).not.toBeNull();
    expect(res!.cid).toMatch(/^snap-/);
    expect(res!.content.length).toBeLessThan(120 * 1024);

    const meta = await sharp(res!.content).metadata();
    expect(meta.width).toBe(640);
    expect(meta.format).toBe('jpeg');
    // EXIF metadata must be stripped
    expect(meta.exif).toBeUndefined();
  });

  it('enforces Invariant I7: person-related alerts return null snapshot', async () => {
    const res = await processSnapshot('sample.jpg', {
      rootDir: tempDir,
      personRelated: true,
    });

    expect(res).toBeNull();
  });

  it('rejects path traversal attempts', () => {
    const safe = resolveSafeSnapshotPath('../../../etc/passwd', tempDir);
    expect(safe).toBeNull();

    const abs = resolveSafeSnapshotPath('/etc/passwd', tempDir);
    expect(abs).toBeNull();
  });

  it('returns null for non-existent files', async () => {
    const res = await processSnapshot('non-existent.jpg', {
      rootDir: tempDir,
      personRelated: false,
    });
    expect(res).toBeNull();
  });
});
