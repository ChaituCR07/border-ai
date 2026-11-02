import { describe, expect, it } from 'vitest';
import {
  renderEmail,
  buildDeepLinks,
  renderTestEmail,
  type EmailModel,
} from '../../src/modules/notifications/rendering.js';

describe('Email Rendering & Security Sanitization', () => {
  const baseModel: EmailModel = {
    alert: {
      alert_id: 'alt-uuid-1234',
      priority: 'CRITICAL',
      created_at: '2026-10-27T02:13:42.000000Z',
      threat_score: 92,
      camera_id: 'CAM-03',
      camera_name: 'North Gate – East',
      event_type: 'RESTRICTED_ZONE_ENTRY',
      summary: 'Restricted Zone Entry',
      plate: 'KA01AB1234',
      person_related: false,
    },
    explanation: [
      { name: 'Restricted zone entry', points: 30 },
      { name: 'Watchlist vehicle', points: 40 },
      { name: 'After-hours movement', points: 10 },
    ],
    journey: {
      text: 'CAM-01 02:07 → CAM-02 02:11 → CAM-03 02:13 (this alert)',
      warnings: [],
    },
    snapshot: {
      cid: 'snap-cid-1',
      content: Buffer.from('fake-jpeg-bytes'),
    },
    links: buildDeepLinks('http://localhost:5173', 'alt-uuid-1234', 'KA01AB1234', '2026-10-27T02:13:42.000000Z'),
    tz: 'Asia/Kolkata',
    include: {
      plate: true,
      snapshot: true,
      journey: true,
      explanation: true,
    },
    kind: 'ALERT',
  };

  it('renders standard CRITICAL vehicle alert with subject, text, HTML and attachment', () => {
    const rendered = renderEmail(baseModel);

    // Subject checks
    expect(rendered.subject).toBe('[CRITICAL] · CAM-03 · Restricted Zone Entry · KA01AB1234 · score 92');

    // Plain text checks
    expect(rendered.text).toContain('CRITICAL ALERT');
    expect(rendered.text).toContain('Camera:        CAM-03 (North Gate – East)');
    expect(rendered.text).toContain('Vehicle:       KA01AB1234');
    expect(rendered.text).toContain('Threat score:  92 / 100');
    expect(rendered.text).toContain('+ Watchlist vehicle              +40');
    expect(rendered.text).toContain('CAM-01 02:07 → CAM-02 02:11 → CAM-03 02:13 (this alert)');
    expect(rendered.text).toContain('http://localhost:5173/?alert=alt-uuid-1234');

    // Attachment check
    expect(rendered.attachments).toHaveLength(1);
    expect(rendered.attachments[0]!.cid).toBe('snap-cid-1');

    // HTML checks
    expect(rendered.html).toContain('cid:snap-cid-1');
    expect(rendered.html).toContain('Why this alert');
    expect(rendered.html).toContain('Journey so far');
    expect(rendered.html).not.toMatch(/<link|<script|<style>.*@import/i);
  });

  it('omits plate completely when include.plate is false', () => {
    const model: EmailModel = {
      ...baseModel,
      include: { ...baseModel.include, plate: false },
    };
    const rendered = renderEmail(model);

    expect(rendered.subject).not.toContain('KA01AB1234');
    expect(rendered.text).not.toContain('Vehicle:');
    expect(rendered.html).not.toContain('KA01AB1234');
  });

  it('omits snapshot attachment when include.snapshot is false or null', () => {
    const model: EmailModel = {
      ...baseModel,
      snapshot: null,
      include: { ...baseModel.include, snapshot: false },
    };
    const rendered = renderEmail(model);

    expect(rendered.attachments).toHaveLength(0);
    expect(rendered.html).not.toContain('<img');
  });

  it('escapes HTML and XSS injection attempts in plate, camera, and explanation', () => {
    const injectedModel: EmailModel = {
      ...baseModel,
      alert: {
        ...baseModel.alert,
        camera_id: '<script>alert("xss")</script>',
        summary: '"><img src=x onerror=alert(1)>',
        plate: '<svg/onload=alert(1)>',
      },
      explanation: [
        { name: '<b>Injected bold</b>', points: 20 },
      ],
    };
    const rendered = renderEmail(injectedModel);

    // Ensure raw tags are escaped
    expect(rendered.html).not.toContain('<script>');
    expect(rendered.html).not.toContain('"><img src=x onerror=alert(1)>');
    expect(rendered.html).not.toContain('<svg/onload=alert(1)>');
    expect(rendered.html).toContain('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
    expect(rendered.html).toContain('&lt;b&gt;Injected bold&lt;/b&gt;');
  });

  it('renders ESCALATION template with red banner and escalation subject', () => {
    const escModel: EmailModel = {
      ...baseModel,
      kind: 'ESCALATION',
      escalation_after_min: 5,
    };
    const rendered = renderEmail(escModel);

    expect(rendered.subject).toContain('[ESCALATION – UNACKNOWLEDGED 5 min]');
    expect(rendered.text).toContain('ESCALATION NOTICE: ALERT UNACKNOWLEDGED FOR 5 MINUTES');
    expect(rendered.html).toContain('UNACKNOWLEDGED FOR 5 MIN');
  });

  it('renders test email correctly', () => {
    const rendered = renderTestEmail('admin@example.org');
    expect(rendered.subject).toContain('[TEST]');
    expect(rendered.text).toContain('admin@example.org');
    expect(rendered.html).toContain('admin@example.org');
  });
});
