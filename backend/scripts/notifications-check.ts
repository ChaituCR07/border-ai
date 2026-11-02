import path from 'node:path';
import dotenv from 'dotenv';
import {
  loadNotificationConfig,
  validateNotificationConfig,
  type NotificationConfig,
} from '../src/modules/notifications/config.js';

dotenv.config();

function runCheck(filePath?: string) {
  const targetPath = filePath || process.env.NOTIFICATIONS_CONFIG || 'configs/notifications.json';
  console.log(`[notifications:check] Validating notifications configuration from ${targetPath}...`);

  let config: NotificationConfig;
  try {
    config = loadNotificationConfig(targetPath);
  } catch (err: any) {
    console.error(`[notifications:check] ERROR loading config: ${err.message}`);
    process.exit(1);
  }

  const allowedDomains = (process.env.NOTIFY_ALLOWED_DOMAINS || 'example.org,border-ai.local')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);

  const result = validateNotificationConfig(config, allowedDomains);

  console.log('\n--- Resolved Routing Table ---');
  for (const r of config.routes) {
    const escStr = r.escalate ? ` (Escalate after ${r.escalate.after_s}s -> ${r.escalate.recipients.join(', ')})` : '';
    console.log(
      `• [${r.name}] Mode: ${r.mode.toUpperCase()} | Priorities: ${r.match.priority.join(', ')} | Recipients: ${r.recipients.join(', ')}${escStr}`
    );
  }
  console.log('------------------------------\n');

  for (const warn of result.warnings) {
    console.warn(`[notifications:check] ⚠️  WARN: ${warn}`);
  }

  if (!result.valid) {
    for (const err of result.errors) {
      console.error(`[notifications:check] ❌ ERROR: ${err}`);
    }
    console.error(`\n[notifications:check] FAILED with ${result.errors.length} error(s).`);
    process.exit(1);
  }

  console.log(
    `[notifications:check] ✓ PASSED! Config is valid (${config.routes.length} routes, cooldown: ${config.cooldown_s}s, max rate: ${config.rate_limit.per_recipient_per_min}/min).`
  );
}

const argFile = process.argv[2];
runCheck(argFile);
