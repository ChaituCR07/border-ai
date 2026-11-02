import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod';

export const PrioritySchema = z.enum(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']);
export type Priority = z.infer<typeof PrioritySchema>;

export const RouteSchema = z
  .object({
    name: z.string().regex(/^[a-z0-9-]{3,40}$/, 'Route name must be 3-40 lowercase alphanumeric or hyphens'),
    match: z
      .object({
        priority: z.array(PrioritySchema).min(1),
        camera_id: z.array(z.string()).optional(),
        event_type: z.array(z.string()).optional(),
      })
      .strict(),
    recipients: z.array(z.string().email()).min(1).max(20),
    mode: z.enum(['immediate', 'digest']),
    digest_window_s: z.number().int().min(60).max(3600).optional(),
    include: z
      .object({
        plate: z.boolean(),
        snapshot: z.boolean(),
        journey: z.boolean(),
        explanation: z.boolean(),
      })
      .strict(),
    escalate: z
      .object({
        after_s: z.number().int().min(30).max(86400),
        recipients: z.array(z.string().email()).min(1),
      })
      .optional(),
  })
  .strict()
  .refine(r => r.mode !== 'digest' || r.digest_window_s !== undefined, {
    message: 'digest routes need digest_window_s',
    path: ['digest_window_s'],
  });

export type Route = z.infer<typeof RouteSchema>;

export const NotificationConfigSchema = z
  .object({
    version: z.number().int().min(1),
    from: z.string().min(5),
    base_url: z.string().url(),
    display_timezone: z.string().default('UTC'),
    catchup_max_age_s: z.number().int().min(60).max(86400).default(3600),
    cooldown_s: z.number().int().min(10).max(86400).default(300),
    rate_limit: z.object({
      per_recipient_per_min: z.number().int().min(1).max(120),
    }),
    max_attempts: z.number().int().min(1).max(20).default(6),
    routes: z.array(RouteSchema).min(1),
  })
  .strict();

export type NotificationConfig = z.infer<typeof NotificationConfigSchema>;

export interface ConfigValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateNotificationConfig(
  config: NotificationConfig,
  allowedDomains: string[] = ['example.org', 'border-ai.local']
): ConfigValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  const routeNames = new Set<string>();
  const prioritiesCovered = new Set<Priority>();

  // Check cooldown warning
  if (config.cooldown_s < 60) {
    warnings.push(`cooldown_s (${config.cooldown_s}s) is less than recommended minimum 60s.`);
  }

  const normalizedAllowed = allowedDomains.map(d => d.trim().toLowerCase());

  for (const route of config.routes) {
    if (routeNames.has(route.name)) {
      errors.push(`Duplicate route name detected: '${route.name}'.`);
    }
    routeNames.add(route.name);

    for (const p of route.match.priority) {
      prioritiesCovered.add(p);
    }

    // Check escalate on non-CRITICAL route
    if (route.escalate && !route.match.priority.includes('CRITICAL')) {
      warnings.push(`Route '${route.name}' defines escalation but match.priority does not include CRITICAL.`);
    }

    // Check recipients against allowed domains
    const allOutside = route.recipients.every(r => {
      const parts = r.split('@');
      const domain = parts[1]?.toLowerCase();
      return !domain || !normalizedAllowed.includes(domain);
    });

    if (allOutside && route.recipients.length > 0) {
      warnings.push(
        `Route '${route.name}' has all recipients outside NOTIFY_ALLOWED_DOMAINS (${normalizedAllowed.join(', ')}). Emails will be SKIPPED.`
      );
    }
  }

  // Check if CRITICAL has a route
  if (!prioritiesCovered.has('CRITICAL')) {
    warnings.push('No route configured for CRITICAL priority alerts.');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

export function loadNotificationConfig(filePath?: string): NotificationConfig {
  const candidatePaths = [
    filePath,
    process.env.NOTIFICATIONS_CONFIG,
    path.resolve(process.cwd(), 'configs/notifications.json'),
    path.resolve(process.cwd(), '../configs/notifications.json'),
  ].filter(Boolean) as string[];

  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      const raw = fs.readFileSync(p, 'utf-8');
      const parsed = JSON.parse(raw);
      return NotificationConfigSchema.parse(parsed);
    }
  }

  throw new Error(
    `Notification config file not found. Looked in: ${candidatePaths.join(', ')}`
  );
}
