import fs from 'node:fs';
import path from 'node:path';
import { ROLE_PERMISSIONS, PERMISSIONS, Permission, Role } from '../src/security/policy.js';

function run() {
  console.log('--- Generating RBAC Matrix Documentation ---');

  const roles: Role[] = ['VIEWER', 'OPERATOR', 'INVESTIGATOR', 'ADMIN'];

  let md = '# Role-Based Access Control (RBAC) Matrix\n\n';
  md += '**Generated On:** ' + new Date().toISOString() + '\n';
  md += '**Source of Truth:** `backend/src/security/policy.ts`\n\n';
  md += '---\n\n';

  md += '## 1. Role to Permission Mapping\n\n';
  md += '| Permission | Description | VIEWER | OPERATOR | INVESTIGATOR | ADMIN |\n';
  md += '|---|---|:---:|:---:|:---:|:---:|\n';

  const descriptions: Record<Permission, string> = {
    'live:view': 'Live MJPEG video stream viewing',
    'alerts:view': 'Query alerts and read threat summaries',
    'alerts:ack': 'Acknowledge pending threat alerts',
    'alerts:resolve': 'Resolve threat alerts with operational disposition',
    'events:view': 'Search historical events and review facets',
    'evidence:view': 'Access unredacted forensic evidence and person snapshots',
    'investigation:journey': 'Multi-camera vehicle journey tracking',
    'investigation:person_search': 'Attribute and biometric search on persons',
    'investigation:sequence': 'Temporal-spatial camera sequence correlation',
    'export:csv': 'Export forensic intelligence to CSV format',
    'watchlist:view': 'Read target license plates and identity descriptions',
    'watchlist:write': 'Register, modify, or delete watchlist entries',
    'config:read': 'View system configuration, thresholds, and topologies (read-only)',
    'config:write': 'Update detection rules, thresholds, and notification policies',
    'cameras:view': 'Inspect camera hardware registry and status',
    'cameras:write': 'Add, edit, or decommission camera devices',
    'topology:write': 'Update spatial adjacency and corridor links',
    'notifications:admin': 'Configure notification delivery, test, and retry queues',
    'users:manage': 'Create users, modify roles, reset passwords, disable accounts',
    'audit:view': 'Query immutable audit log and verify cryptographic hash chain',
    'retention:run': 'Trigger automated retention pruning tasks',
    'system:status': 'Query high-level telemetry and node status',
    'system:detail': 'Access deep queue diagnostics, redis memory, and internal metrics',
    'realtime:subscribe': 'Subscribe to realtime WebSocket event and alert streams',
  };

  for (const perm of PERMISSIONS) {
    const desc = descriptions[perm] ?? 'Operational permission';
    const row = [
      `\`${perm}\``,
      desc,
      ROLE_PERMISSIONS.VIEWER.has(perm) ? '✓' : '✗',
      ROLE_PERMISSIONS.OPERATOR.has(perm) ? '✓' : '✗',
      ROLE_PERMISSIONS.INVESTIGATOR.has(perm) ? (perm === 'config:read' ? '✓ (*Limited*)' : '✓') : '✗',
      ROLE_PERMISSIONS.ADMIN.has(perm) ? '✓' : '✗',
    ];
    md += `| ${row.join(' | ')} |\n`;
  }

  md += '\n---\n\n';
  md += '## 2. Endpoint to Permission Register\n\n';
  md += '| HTTP Method | Endpoint Path | Required Permission | Public / Protected |\n';
  md += '|---|---|---|:---:|\n';

  const endpoints = [
    { method: 'GET', path: '/health', perm: 'public', public: true },
    { method: 'GET', path: '/ready', perm: 'public', public: true },
    { method: 'GET', path: '/.well-known/jwks.json', perm: 'public', public: true },
    { method: 'POST', path: '/api/auth/login', perm: 'public', public: true },
    { method: 'POST', path: '/api/auth/refresh', perm: 'public', public: true },
    { method: 'POST', path: '/api/auth/logout', perm: 'system:status', public: false },
    { method: 'POST', path: '/api/auth/logout-all', perm: 'system:status', public: false },
    { method: 'GET', path: '/api/auth/me', perm: 'system:status', public: false },
    { method: 'POST', path: '/api/auth/change-password', perm: 'system:status', public: false },
    { method: 'GET', path: '/api/cameras', perm: 'cameras:view', public: false },
    { method: 'POST', path: '/api/cameras', perm: 'cameras:write', public: false },
    { method: 'GET', path: '/api/cameras/:id', perm: 'cameras:view', public: false },
    { method: 'PUT', path: '/api/cameras/:id', perm: 'cameras:write', public: false },
    { method: 'GET', path: '/api/events', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/events/:id', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/events/:id/context', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/alerts', perm: 'alerts:view', public: false },
    { method: 'GET', path: '/api/alerts/:id', perm: 'alerts:view', public: false },
    { method: 'PATCH', path: '/api/alerts/:id/acknowledge', perm: 'alerts:ack', public: false },
    { method: 'PATCH', path: '/api/alerts/:id/resolve', perm: 'alerts:resolve', public: false },
    { method: 'GET', path: '/api/investigation/facets', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/investigation/suggest', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/investigation/journey', perm: 'investigation:journey', public: false },
    { method: 'GET', path: '/api/investigation/export.csv', perm: 'export:csv', public: false },
    { method: 'GET', path: '/api/correlation/sequence', perm: 'investigation:sequence', public: false },
    { method: 'GET', path: '/api/topology', perm: 'cameras:view', public: false },
    { method: 'GET', path: '/api/watchlist', perm: 'watchlist:view', public: false },
    { method: 'POST', path: '/api/watchlist', perm: 'watchlist:write', public: false },
    { method: 'DELETE', path: '/api/watchlist/:id', perm: 'watchlist:write', public: false },
    { method: 'GET', path: '/api/analytics/events', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/analytics/cameras', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/analytics/threats', perm: 'events:view', public: false },
    { method: 'GET', path: '/api/analytics/resolutions', perm: 'alerts:resolve', public: false },
    { method: 'GET', path: '/api/snapshots/*', perm: 'evidence:view', public: false },
    { method: 'GET', path: '/api/config/public', perm: 'public', public: true },
    { method: 'GET', path: '/api/system/status', perm: 'system:status', public: false },
    { method: 'GET', path: '/api/realtime/status', perm: 'system:status', public: false },
    { method: 'GET', path: '/api/ws', perm: 'realtime:subscribe', public: false },
    { method: 'GET', path: '/api/users', perm: 'users:manage', public: false },
    { method: 'POST', path: '/api/users', perm: 'users:manage', public: false },
    { method: 'GET', path: '/api/users/:id', perm: 'users:manage', public: false },
    { method: 'PATCH', path: '/api/users/:id', perm: 'users:manage', public: false },
    { method: 'POST', path: '/api/users/:id/reset-password', perm: 'users:manage', public: false },
    { method: 'POST', path: '/api/users/:id/disable', perm: 'users:manage', public: false },
    { method: 'DELETE', path: '/api/users/:id', perm: 'users:manage', public: false },
    { method: 'GET', path: '/api/notifications', perm: 'notifications:admin', public: false },
    { method: 'GET', path: '/api/notifications/status', perm: 'notifications:admin', public: false },
    { method: 'POST', path: '/api/notifications/test', perm: 'notifications:admin', public: false },
    { method: 'POST', path: '/api/notifications/retry/:id', perm: 'notifications:admin', public: false },
  ];

  for (const ep of endpoints) {
    md += `| ${ep.method} | \`${ep.path}\` | \`${ep.perm}\` | ${ep.public ? 'Public' : 'Protected'} |\n`;
  }

  const outPath = path.resolve(process.cwd(), '../docs/security/rbac_matrix.md');
  const targetPath = fs.existsSync(path.dirname(outPath))
    ? outPath
    : path.resolve(process.cwd(), 'docs/security/rbac_matrix.md');

  fs.writeFileSync(targetPath, md, 'utf-8');
  console.log(`RBAC matrix generated at: ${targetPath}`);
}

run();
