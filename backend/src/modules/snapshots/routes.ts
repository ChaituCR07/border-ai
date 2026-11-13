import fs from 'node:fs';
import path from 'node:path';
import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import { notFound, validationError } from '../../common/errors.js';
import { hasPermission } from '../../security/policy.js';
import { Role } from '../../security/jwt.js';

export interface SnapshotRouteDeps {
  snapshotDir: string;
}

const ALLOWED_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp']);

const REDACTED_PERSON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240" fill="#1e293b">
  <rect width="320" height="240" fill="#0f172a"/>
  <circle cx="160" cy="90" r="35" fill="#475569"/>
  <path d="M100 190 C100 145 130 135 160 135 C190 135 220 145 220 190 Z" fill="#475569"/>
  <text x="160" y="215" font-family="sans-serif" font-size="12" fill="#94a3b8" text-anchor="middle">
    [Evidence Redacted for Viewer Role]
  </text>
</svg>`;

export function snapshotRoutes(deps: SnapshotRouteDeps): FastifyPluginAsync {
  return async (fastify: FastifyInstance) => {
    fastify.get('/snapshots/*', { config: { permission: 'events:view' } }, async (req, reply) => {
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

      // Check for person-related evidence
      const isPersonEvidence =
        wildcard.toLowerCase().includes('person') ||
        wildcard.toLowerCase().includes('face');

      const actorRole = (req.actor?.role || 'VIEWER') as Role;
      const canViewRawEvidence = hasPermission(actorRole, 'evidence:view');

      // Privacy policy: Viewers requesting person evidence receive redacted placeholder
      if (isPersonEvidence && !canViewRawEvidence) {
        return reply
          .header('Content-Type', 'image/svg+xml')
          .header('Cache-Control', 'no-store')
          .send(REDACTED_PERSON_SVG);
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
