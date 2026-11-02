import { type Priority, type Route } from './config.js';
import { esc, sanitizeText, formatTimeInTz } from './templates/escape.js';

export interface EmailAttachment {
  filename?: string;
  content: Buffer | string;
  cid?: string;
  contentType?: string;
}

export interface RenderedEmail {
  subject: string;
  text: string;
  html: string;
  attachments: EmailAttachment[];
}

export interface EmailModel {
  alert: {
    alert_id: string;
    priority: Priority;
    created_at: string;
    threat_score: number;
    camera_id: string;
    camera_name?: string;
    event_type: string;
    summary: string;
    plate?: string | null;
    person_related?: boolean;
  };
  explanation: Array<{ name: string; points: number; detail?: string }> | null;
  journey: { text: string; warnings: string[] } | null;
  snapshot: { cid: string; content: Buffer } | null;
  links: { alert: string; investigate: string | null; journey: string | null };
  tz: string;
  include: Route['include'];
  escalation_after_min?: number;
  kind?: 'ALERT' | 'ESCALATION' | 'DIGEST' | 'TEST';
}

export function buildDeepLinks(baseUrl: string, alertId: string, plate: string | null, createdAtIso: string) {
  const ts = new Date(createdAtIso).getTime();
  const from1h = new Date(ts - 3600 * 1000).toISOString();
  const to1h = new Date(ts + 3600 * 1000).toISOString();
  const from2h = new Date(ts - 7200 * 1000).toISOString();
  const toEnd = new Date(ts + 60 * 1000).toISOString();

  const alertParam = new URLSearchParams({ alert: alertId });
  const alertLink = `${baseUrl}/?${alertParam.toString()}`;

  let investigateLink: string | null = null;
  let journeyLink: string | null = null;

  if (plate) {
    const invParams = new URLSearchParams({
      plate,
      from: from1h,
      to: to1h,
    });
    investigateLink = `${baseUrl}/investigation?${invParams.toString()}`;

    const jParams = new URLSearchParams({
      plate,
      view: 'journey',
      from: from2h,
      to: toEnd,
    });
    journeyLink = `${baseUrl}/investigation?${jParams.toString()}`;
  }

  return {
    alert: alertLink,
    investigate: investigateLink,
    journey: journeyLink,
  };
}

export function renderEmail(model: EmailModel): RenderedEmail {
  const isEscalation = model.kind === 'ESCALATION';
  const a = model.alert;
  const plateText = model.include.plate && a.plate ? a.plate : null;
  const camDisplay = a.camera_name ? `${a.camera_id} (${a.camera_name})` : a.camera_id;

  // Build subject
  const subjectPrefix = isEscalation
    ? `[ESCALATION – UNACKNOWLEDGED ${model.escalation_after_min ?? 5} min]`
    : `[${a.priority}]`;

  const subjectParts = [subjectPrefix, a.camera_id, a.summary || a.event_type];
  if (plateText) {
    subjectParts.push(plateText);
  }
  subjectParts.push(`score ${a.threat_score}`);
  const subject = subjectParts.join(' · ');

  // Format times
  const timeUtc = `${formatTimeInTz(a.created_at, 'UTC')} UTC`;
  const timeLocal = model.tz !== 'UTC' ? `  (${formatTimeInTz(a.created_at, model.tz)} ${model.tz})` : '';

  // Plain-text parts
  let text = '';
  if (isEscalation) {
    text += `⚠️  ESCALATION NOTICE: ALERT UNACKNOWLEDGED FOR ${model.escalation_after_min ?? 5} MINUTES\n`;
    text += `The following ${a.priority} threat alert requires immediate command center intervention.\n\n`;
  }

  text += `${a.priority} ALERT\n\n`;
  text += `Camera:        ${sanitizeText(camDisplay)}\n`;
  if (plateText) {
    text += `Vehicle:       ${sanitizeText(plateText)}\n`;
  }
  text += `Event:         ${sanitizeText(a.summary || a.event_type)}\n`;
  text += `Threat score:  ${a.threat_score} / 100\n`;
  text += `Time:          ${timeUtc}${timeLocal}\n\n`;

  if (model.include.explanation && model.explanation && model.explanation.length > 0) {
    text += `Why this alert:\n`;
    for (const f of model.explanation) {
      text += `  + ${sanitizeText(f.name).padEnd(30)} +${f.points}\n`;
    }
    text += `\n`;
  }

  if (model.include.journey && model.journey && model.journey.text) {
    text += `Journey so far:\n`;
    text += `  ${sanitizeText(model.journey.text)}\n`;
    if (model.journey.warnings && model.journey.warnings.length > 0) {
      for (const w of model.journey.warnings) {
        text += `  ⚠️  ${sanitizeText(w)}\n`;
      }
    }
    text += `\n`;
  }

  text += `Open alert:       ${model.links.alert}\n`;
  if (plateText && model.links.investigate) {
    text += `Investigate:      ${model.links.investigate}\n`;
  }
  if (plateText && model.links.journey) {
    text += `Journey view:     ${model.links.journey}\n`;
  }

  text += `\n---\nAutomated alert from Border-AI Surveillance System. Do not forward outside response team.\n`;

  // HTML rendering
  const bannerColor = a.priority === 'CRITICAL' ? '#dc2626' : '#ea580c';
  const escalationBanner = isEscalation
    ? `<div style="background-color: #7f1d1d; color: #fef2f2; padding: 12px; font-weight: bold; text-align: center; border-radius: 4px; margin-bottom: 16px;">
        ⚠️ UNACKNOWLEDGED FOR ${model.escalation_after_min ?? 5} MIN &middot; ESCALATED TO DUTY OFFICER
       </div>`
    : '';

  let explanationHtml = '';
  if (model.include.explanation && model.explanation && model.explanation.length > 0) {
    explanationHtml = `
      <div style="margin-top: 16px;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.05em;">Why this alert</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          ${model.explanation
            .map(
              f => `
            <tr style="border-bottom: 1px solid #334155;">
              <td style="padding: 6px 0; color: #f1f5f9;">+ ${esc(f.name)}</td>
              <td style="padding: 6px 0; text-align: right; font-weight: bold; color: #38bdf8;">+${esc(f.points)}</td>
            </tr>`
            )
            .join('')}
        </table>
      </div>`;
  }

  let journeyHtml = '';
  if (model.include.journey && model.journey && model.journey.text) {
    journeyHtml = `
      <div style="margin-top: 16px;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.05em;">Journey so far</h3>
        <div style="background-color: #0f172a; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #38bdf8;">
          ${esc(model.journey.text)}
        </div>
        ${
          model.journey.warnings && model.journey.warnings.length > 0
            ? model.journey.warnings
                .map(
                  w => `
          <div style="margin-top: 4px; color: #f59e0b; font-size: 12px;">⚠️ ${esc(w)}</div>`
                )
                .join('')
            : ''
        }
      </div>`;
  }

  let snapshotHtml = '';
  const attachments: EmailAttachment[] = [];

  if (model.include.snapshot && model.snapshot) {
    attachments.push({
      filename: 'snapshot.jpg',
      content: model.snapshot.content,
      cid: model.snapshot.cid,
      contentType: 'image/jpeg',
    });
    snapshotHtml = `
      <div style="margin-top: 16px;">
        <img src="cid:${esc(model.snapshot.cid)}" alt="Evidence snapshot for camera ${esc(
      a.camera_id
    )}" style="max-width: 100%; height: auto; border-radius: 4px; border: 1px solid #334155; display: block;" />
      </div>`;
  }

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${esc(subject)}</title>
</head>
<body style="margin: 0; padding: 20px; background-color: #090d16; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 8px; overflow: hidden; border: 1px solid #334155;">
    <div style="background-color: ${bannerColor}; color: #ffffff; padding: 16px 20px; font-size: 16px; font-weight: bold; letter-spacing: 0.05em;">
      🚨 ${esc(a.priority)} THREAT ALERT &middot; SCORE ${esc(a.threat_score)}/100
    </div>
    <div style="padding: 20px;">
      ${escalationBanner}
      <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
        <tr>
          <td style="padding: 6px 0; color: #94a3b8; width: 120px;">Camera:</td>
          <td style="padding: 6px 0; font-weight: bold; color: #f8fafc;">${esc(camDisplay)}</td>
        </tr>
        ${
          plateText
            ? `<tr>
          <td style="padding: 6px 0; color: #94a3b8;">Vehicle:</td>
          <td style="padding: 6px 0; font-family: monospace; font-weight: bold; color: #38bdf8;">${esc(plateText)}</td>
        </tr>`
            : ''
        }
        <tr>
          <td style="padding: 6px 0; color: #94a3b8;">Event:</td>
          <td style="padding: 6px 0; color: #f8fafc;">${esc(a.summary || a.event_type)}</td>
        </tr>
        <tr>
          <td style="padding: 6px 0; color: #94a3b8;">Time:</td>
          <td style="padding: 6px 0; color: #f8fafc;">${esc(timeUtc)}<span style="color: #94a3b8;">${esc(timeLocal)}</span></td>
        </tr>
      </table>

      ${snapshotHtml}
      ${explanationHtml}
      ${journeyHtml}

      <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #334155; text-align: center;">
        <a href="${esc(model.links.alert)}" style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: 500; font-size: 14px; margin-right: 8px;">Open Alert in Dashboard &rarr;</a>
        ${
          plateText && model.links.investigate
            ? `<a href="${esc(model.links.investigate)}" style="display: inline-block; background-color: #334155; color: #f8fafc; padding: 10px 16px; text-decoration: underline; border-radius: 4px; font-size: 14px;">Investigate Vehicle</a>`
            : ''
        }
      </div>
    </div>
    <div style="background-color: #0f172a; padding: 12px 20px; font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid #1e293b;">
      Automated alert from Border-AI Surveillance System &middot; Handle per security retention policy &middot; Do not forward outside response team
    </div>
  </div>
</body>
</html>`;

  return {
    subject,
    text,
    html,
    attachments,
  };
}

export function renderTestEmail(recipient: string): RenderedEmail {
  const subject = '[TEST] Border-AI Notification System Connectivity Test';
  const text = `This is a test email from the Border-AI Surveillance System.\nRecipient: ${recipient}\nStatus: System connectivity verified.`;
  const html = `<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
  <div style="max-width: 500px; margin: 0 auto; background-color: #1e293b; padding: 20px; border-radius: 6px;">
    <h2 style="color: #38bdf8;">[TEST] Border-AI Email Notification</h2>
    <p>This is a verified test email sent to <strong>${esc(recipient)}</strong>.</p>
    <p style="font-size: 12px; color: #94a3b8;">Timestamp: ${new Date().toISOString()}</p>
  </div>
</body>
</html>`;

  return {
    subject,
    text,
    html,
    attachments: [],
  };
}
