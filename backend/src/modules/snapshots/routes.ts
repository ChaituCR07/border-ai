import fs from 'node:fs';
import path from 'node:path';
import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import { notFound, validationError } from '../../common/errors.js';

export interface SnapshotRouteDeps {
  snapshotDir: string;
}

const ALLOWED_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp']);

export function snapshotRoutes(deps: SnapshotRouteDeps): FastifyPluginAsync {
  return async (fastify: FastifyInstance) => {
    fastify.get('/snapshots/*', async (req, reply) => {
      const wildcard = (req.params as { '*': string })['*'];
      if (!wildcard) throw notFound('Snapshot');

      // Reject path traversal attempts in raw string
      if (wildcard.includes('..') || wildcard.includes('\0')) {
        throw validationError('Invalid snapshot path');
      }

      const root = path.resolve(deps.snapshotDir);
      const abs = path.resolve(root, wildcard);

      // Verify resolved path stays strictly inside root
      if (!abs.startsWith(root + path.sep)) {
        throw validationError('Invalid snapshot path');
      }

      const ext = path.extname(abs).toLowerCase();
      if (!ALLOWED_EXTENSIONS.has(ext)) {
        throw notFound('Snapshot format not supported');
      }

      if (!fs.existsSync(abs)) {
        throw notFound('Snapshot');
      }

      let mimeType = 'image/jpeg';
      if (ext === '.png') mimeType = 'image/png';
      else if (ext === '.webp') mimeType = 'image/webp';

      const stream = fs.createReadStream(abs);
      return reply
        .header('Content-Type', mimeType)
        .header('Cache-Control', 'private, max-age=3600')
        .send(stream);
    });
  };
}
