import { loadThreatThresholdConfig, tierForScore } from '../src/config/thresholds.js';
import { loadNotificationConfig, validateNotificationConfig } from '../src/modules/notifications/config.js';
import { matchRoutes, groupKey, decide, sanitizeHeader } from '../src/modules/notifications/policy.js';
import { renderEmail, buildDeepLinks, type EmailModel } from '../src/modules/notifications/rendering.js';
import { processSnapshot } from '../src/modules/notifications/snapshot.js';

async function runNotificationsSmoke() {
  console.log('[smoke:notifications] Starting Day 20 Alert Generation & Notifications smoke verification...');

  // 1. Single Source of Truth Threat Thresholds
  const threshConfig = loadThreatThresholdConfig('../configs/threat_thresholds.json');
  if (threshConfig.version !== 1 || threshConfig.tiers.length !== 4) {
    throw new Error('Invalid threat thresholds configuration');
  }
  const lowClass = tierForScore(10, threshConfig);
  const medClass = tierForScore(30, threshConfig);
  const highClass = tierForScore(65, threshConfig);
  const critClass = tierForScore(85, threshConfig);

  if (lowClass !== 'LOW' || medClass !== 'MEDIUM' || highClass !== 'HIGH' || critClass !== 'CRITICAL') {
    throw new Error(`Score classification mismatch: low=${lowClass}, med=${medClass}, high=${highClass}, crit=${critClass}`);
  }
  console.log('[smoke:notifications] ✓ Threat thresholds verified (parity across LOW, MEDIUM, HIGH, CRITICAL).');

  // 2. Notification Configuration Schema & Validation
  const notifConfig = loadNotificationConfig('../configs/notifications.json');
  const validation = validateNotificationConfig(notifConfig, ['example.org', 'border-ai.local']);
  if (!validation.valid) {
    throw new Error(`Notification configuration validation failed: ${validation.errors.join('; ')}`);
  }
  console.log(`[smoke:notifications] ✓ Notification configuration valid: ${notifConfig.routes.length} routes, cooldown=${notifConfig.cooldown_s}s, max_attempts=${notifConfig.max_attempts}`);

  // 3. Routing Policy, Cooldowns & Priority Upgrade Bypass
  const alertCtx = {
    alert_id: 'alt-smoke-1',
    priority: 'CRITICAL' as const,
    created_at: new Date().toISOString(),
    camera_id: 'CAM-03',
    event_type: 'RESTRICTED_ZONE_ENTRY',
    plate: 'KA01AB1234',
    person_related: false,
  };

  const critRoutes = matchRoutes(notifConfig, alertCtx);
  if (critRoutes.length === 0) {
    throw new Error('Expected at least one route matching CRITICAL on CAM-03');
  }
  console.log(`[smoke:notifications] ✓ Route matching verified (${critRoutes.length} matched routes for CRITICAL).`);

  const route = critRoutes[0]!;
  const key = groupKey(alertCtx);
  if (!key.includes('CAM-03') || !key.includes('plate:')) {
    throw new Error(`Unexpected group key: ${key}`);
  }

  // Cooldown decision: repeat alert of same priority within cooldown window is suppressed
  const repeatDecision = decide(route, alertCtx, {
    priority: 'CRITICAL',
    created_at_age_s: 60, // 60s ago < 300s
  }, notifConfig.cooldown_s);

  if (repeatDecision.action !== 'SKIP' || repeatDecision.reason !== 'cooldown') {
    throw new Error(`Expected cooldown suppression for repeat alert, got: ${JSON.stringify(repeatDecision)}`);
  }

  // Priority Upgrade bypass: previous was HIGH, current is CRITICAL -> allowed despite cooldown
  const upgradeDecision = decide(route, alertCtx, {
    priority: 'HIGH',
    created_at_age_s: 60,
  }, notifConfig.cooldown_s);

  if (upgradeDecision.action !== 'SEND') {
    throw new Error(`Expected priority upgrade bypass for HIGH -> CRITICAL, got: ${JSON.stringify(upgradeDecision)}`);
  }
  console.log('[smoke:notifications] ✓ Policy decisions verified: cooldowns suppress, priority upgrade bypasses.');

  // 4. Privacy Invariant I7: Person-related snapshot suppression
  const personSnapshot = await processSnapshot('any/path/snapshot.jpg', { personRelated: true });
  if (personSnapshot !== null) {
    throw new Error('Invariant I7 violation: person-related alert must return null snapshot');
  }
  console.log('[smoke:notifications] ✓ Privacy Invariant I7 verified (person-related snapshots strictly redacted).');

  // 5. Header Sanitization
  const cleanHeader = sanitizeHeader('Critical Alert\r\nBcc: evil@attacker.org\n');
  if (cleanHeader.includes('\r') || cleanHeader.includes('\n')) {
    throw new Error(`Header injection sanitization failed: ${cleanHeader}`);
  }
  console.log('[smoke:notifications] ✓ RFC 5322 header injection defense verified (CRLF stripped).');

  // 6. Email Rendering & Deep Links
  const nowIso = new Date().toISOString();
  const links = buildDeepLinks(notifConfig.base_url, 'alt-smoke-999', 'KA01AB1234', nowIso);
  if (!links.alert.includes('/?alert=alt-smoke-999') || !links.investigate?.includes('KA01AB1234')) {
    throw new Error(`Deep links unexpected: ${JSON.stringify(links)}`);
  }

  const emailModel: EmailModel = {
    alert: {
      alert_id: 'alt-smoke-999',
      priority: 'CRITICAL',
      created_at: nowIso,
      camera_name: 'Gate 3 Main Entrance',
      camera_id: 'CAM-03',
      event_type: 'RESTRICTED_ZONE_ENTRY',
      summary: 'Restricted zone intrusion detected',
      plate: 'KA01AB1234',
      threat_score: 92,
      person_related: false,
    },
    explanation: [{ name: 'Restricted Zone', points: 40 }],
    journey: { text: 'CAM-01 10:00 -> CAM-02 10:06 -> CAM-03 10:12', warnings: [] },
    links,
    snapshot: null,
    tz: 'UTC',
    include: { plate: true, snapshot: true, journey: true, explanation: true },
  };

  const rendered = renderEmail(emailModel);
  if (!rendered.subject.includes('[CRITICAL]') || !rendered.html.includes('alt-smoke-999') || !rendered.text.includes('Gate 3')) {
    throw new Error('Email rendering verification failed');
  }
  console.log(`[smoke:notifications] ✓ Email rendering verified: subject="${rendered.subject}", html=${rendered.html.length}b, text=${rendered.text.length}b`);

  console.log('\n================================================================');
  console.log('  ALL DAY 20 ALERT GENERATION & NOTIFICATIONS SMOKE CHECKS PASSED');
  console.log('================================================================\n');
}

runNotificationsSmoke().catch((err) => {
  console.error('[smoke:notifications] Fatal failure:', err);
  process.exit(1);
});
