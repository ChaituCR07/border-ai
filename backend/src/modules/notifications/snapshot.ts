import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import sharp from 'sharp';

export interface ProcessedSnapshot {
  cid: string;
  content: Buffer;
}

export function resolveSafeSnapshotPath(rawPath: string, rootDir: string): string | null {
  if (!rawPath || typeof rawPath !== 'string') {
    return null;
  }

  // Reject path traversal tokens
  const normalized = rawPath.replace(/\\/g, '/');
  if (normalized.includes('..') || path.isAbsolute(normalized)) {
    return null;
  }

  const resolved = path.resolve(rootDir, normalized);
  const resolvedRoot = path.resolve(rootDir);

  // Must remain within rootDir
  if (!resolved.startsWith(resolvedRoot)) {
    return null;
  }

  return resolved;
}

export async function processSnapshot(
  filePath: string | null | undefined,
  options: {
    rootDir?: string;
    personRelated?: boolean;
    maxBytes?: number;
    maxWidth?: number;
  } = {}
): Promise<ProcessedSnapshot | null> {
  const {
    rootDir = path.resolve(process.cwd(), '../outputs'),
    personRelated = false,
    maxBytes = 5 * 1024 * 1024, // 5MB cap
    maxWidth = 640,
  } = options;

  // Invariant I7: person-related alerts NEVER embed imagery in email
  if (personRelated || !filePath) {
    return null;
  }

  const safePath = resolveSafeSnapshotPath(filePath, rootDir) || (fs.existsSync(filePath) ? filePath : null);
  if (!safePath || !fs.existsSync(safePath)) {
    return null;
  }

  const stat = fs.statSync(safePath);
  if (stat.size > maxBytes) {
    return null;
  }

  try {
    const rawBuf = fs.readFileSync(safePath);

    // sharp strips EXIF metadata by default when .withMetadata() is not called
    let processed = await sharp(rawBuf)
      .rotate()
      .resize({ width: maxWidth, withoutEnlargement: true })
      .jpeg({ quality: 80 })
      .toBuffer();

    // If output exceeds 120 KB, compress with lower quality once
    if (processed.length > 120 * 1024) {
      processed = await sharp(rawBuf)
        .rotate()
        .resize({ width: maxWidth, withoutEnlargement: true })
        .jpeg({ quality: 60 })
        .toBuffer();
    }

    const cid = `snap-${crypto.randomUUID()}`;
    return {
      cid,
      content: processed,
    };
  } catch (err) {
    console.warn('[snapshot] Downscale/strip processing failed:', err);
    return null;
  }
}
