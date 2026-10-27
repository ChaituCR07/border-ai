import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { ServerMessage, ClientMessage, AlertView } from '../src/index';

describe('Shared WebSocket Protocol Validation', () => {
  const readSample = (file: string) => {
    const fullPath = path.resolve(__dirname, '../../../docs/api/ws-samples', file);
    return JSON.parse(fs.readFileSync(fullPath, 'utf8'));
  };

  it('validates hello message sample', () => {
    const data = readSample('hello.json');
    const parsed = ServerMessage.safeParse(data);
    expect(parsed.success).toBe(true);
  });

  it('validates heartbeat message sample', () => {
    const data = readSample('heartbeat.json');
    const parsed = ServerMessage.safeParse(data);
    expect(parsed.success).toBe(true);
  });

  it('validates alert.created message sample', () => {
    const data = readSample('alert-created.json');
    const parsed = ServerMessage.safeParse(data);
    expect(parsed.success).toBe(true);
  });

  it('validates alert.updated message sample', () => {
    const data = readSample('alert-updated.json');
    const parsed = ServerMessage.safeParse(data);
    expect(parsed.success).toBe(true);
  });

  it('validates resync_required message sample', () => {
    const data = readSample('resync-required.json');
    const parsed = ServerMessage.safeParse(data);
    expect(parsed.success).toBe(true);
  });

  it('validates client ping message sample', () => {
    const data = readSample('ping.json');
    const parsed = ClientMessage.safeParse(data);
    expect(parsed.success).toBe(true);
  });

  it('strictly rejects any biometric fields in AlertView (ADR 0009 / ADR 0022)', () => {
    const sample = readSample('alert-created.json');
    const illegalAlert = {
      ...sample.data.alert,
      embedding: [0.12, 0.45, 0.88], // Forbidden biometrics
    };
    const parsed = AlertView.safeParse(illegalAlert);
    expect(parsed.success).toBe(false);
  });

  it('fails safeParse on unknown message type for graceful client ignoring', () => {
    const unknownMsg = {
      v: 1,
      type: 'future_feature_broadcast',
      seq: 99,
      data: {},
    };
    const parsed = ServerMessage.safeParse(unknownMsg);
    expect(parsed.success).toBe(false);
  });
});
