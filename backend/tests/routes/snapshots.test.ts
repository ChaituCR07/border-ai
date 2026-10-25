import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import fs from 'node:fs';
import path from 'node:path';
import { createTestApp } from '../helpers/test-app.js';

describe('Snapshots security & serving routes', () => {
  let app: FastifyInstance;
  const snapshotRoot = path.resolve('./tests/fixtures/snapshots');

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;

    fs.mkdirSync(path.join(snapshotRoot, 'CAM-01'), { recursive: true });
    fs.writeFileSync(path.join(snapshotRoot, 'CAM-01/test.jpg'), Buffer.from([0xff, 0xd8, 0xff, 0xe0]));
  });

  it('serves valid snapshot with Content-Type and Cache-Control headers', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/CAM-01/test.jpg',
    });

    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toBe('image/jpeg');
    expect(res.headers['cache-control']).toBe('private, max-age=3600');
  });

  it('rejects path traversal variants safely (400 or 404, never leaks files)', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/../../etc/passwd',
    });

    expect([400, 404]).toContain(res.statusCode);
    expect(res.body).not.toContain('root:');
  });

  it('returns 404 for non-image extension', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/CAM-01/secret.txt',
    });

    expect(res.statusCode).toBe(404);
  });

  it('returns 404 for missing snapshot', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/snapshots/CAM-01/nonexistent.jpg',
    });

    expect(res.statusCode).toBe(404);
  });
});
