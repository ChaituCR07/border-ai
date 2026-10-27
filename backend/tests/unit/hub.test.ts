import { describe, it, expect, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { Hub } from '../../src/realtime/hub';
import { WS_CLOSE, makeAlertView } from '@border-ai/protocol';
import type { WebSocket } from 'ws';

class FakeWebSocket extends EventEmitter {
  readyState = 1; // 1 = OPEN
  bufferedAmount = 0;
  sent: string[] = [];
  closedWith?: { code: number; reason?: string };
  terminated = false;
  pings = 0;

  send(data: string) {
    this.sent.push(data);
  }

  ping() {
    this.pings += 1;
  }

  close(code: number, reason?: string) {
    this.readyState = 2; // CLOSING
    this.closedWith = { code, reason };
    this.emit('close');
  }

  terminate() {
    this.terminated = true;
    this.readyState = 3; // CLOSED
    this.emit('close');
  }
}

describe('WebSocket Hub Unit Tests', () => {
  it('sends hello message on client add with valid epoch and seq=0', () => {
    const hub = new Hub();
    const ws = new FakeWebSocket() as unknown as WebSocket;

    const clientId = hub.add(ws, { id: 'test-user' });
    expect(clientId).toBeDefined();
    expect(hub.size).toBe(1);

    const fake = ws as unknown as FakeWebSocket;
    expect(fake.sent.length).toBe(1);

    const msg = JSON.parse(fake.sent[0]!);
    expect(msg.type).toBe('hello');
    expect(msg.server_epoch).toBe(hub.epoch);
    expect(msg.seq).toBe(0);
  });

  it('broadcastState increments seq by 1 and transmits to all connected clients', () => {
    const hub = new Hub();
    const ws1 = new FakeWebSocket() as unknown as WebSocket;
    const ws2 = new FakeWebSocket() as unknown as WebSocket;

    hub.add(ws1);
    hub.add(ws2);

    expect(hub.currentSeq).toBe(0);

    const alert = makeAlertView();
    hub.broadcastState({
      v: 1,
      type: 'alert.created',
      data: { alert },
    });

    expect(hub.currentSeq).toBe(1);

    const fake1 = ws1 as unknown as FakeWebSocket;
    const fake2 = ws2 as unknown as FakeWebSocket;

    expect(fake1.sent.length).toBe(2); // hello + alert.created
    expect(fake2.sent.length).toBe(2);

    const m1 = JSON.parse(fake1.sent[1]!);
    expect(m1.type).toBe('alert.created');
    expect(m1.seq).toBe(1);
    expect(m1.data.alert.alert_id).toBe(alert.alert_id);
  });

  it('heartbeat tick does not increment seq and pings clients', () => {
    const hub = new Hub();
    const ws = new FakeWebSocket() as unknown as WebSocket;
    hub.add(ws);

    const fake = ws as unknown as FakeWebSocket;
    fake.emit('pong'); // Mark alive

    hub.tick();

    expect(fake.pings).toBe(1);
    expect(hub.currentSeq).toBe(0);

    const lastMsg = JSON.parse(fake.sent[fake.sent.length - 1]!);
    expect(lastMsg.type).toBe('heartbeat');
    expect(lastMsg.seq).toBe(0);
  });

  it('terminates unresponsive clients that missed pong cycle on subsequent tick', () => {
    const hub = new Hub();
    const ws = new FakeWebSocket() as unknown as WebSocket;
    hub.add(ws);

    const fake = ws as unknown as FakeWebSocket;
    expect(hub.size).toBe(1);

    // First tick: marks alive=false and sends ping
    hub.tick();
    expect(hub.size).toBe(1);
    expect(fake.terminated).toBe(false);

    // Second tick without pong: terminates dead client
    hub.tick();
    expect(fake.terminated).toBe(true);
    expect(hub.size).toBe(0);
  });

  it('drops slow consumers exceeding maxBufferedBytes with 1013 close code', () => {
    const hub = new Hub({ maxBufferedBytes: 100 });
    const ws = new FakeWebSocket() as unknown as WebSocket;
    hub.add(ws);

    const fake = ws as unknown as FakeWebSocket;
    fake.bufferedAmount = 200; // Over 100 byte limit

    hub.broadcastState({
      v: 1,
      type: 'resync_required',
      reason: 'test',
    });

    expect(fake.closedWith).toEqual({
      code: WS_CLOSE.TRY_AGAIN,
      reason: 'slow consumer',
    });
    expect(hub.size).toBe(0);
  });

  it('rejects connections when maxClients ceiling is reached with 1013', () => {
    const hub = new Hub({ maxClients: 1 });
    const ws1 = new FakeWebSocket() as unknown as WebSocket;
    const ws2 = new FakeWebSocket() as unknown as WebSocket;

    const id1 = hub.add(ws1);
    expect(id1).toBeDefined();

    const id2 = hub.add(ws2);
    expect(id2).toBeNull();

    const fake2 = ws2 as unknown as FakeWebSocket;
    expect(fake2.closedWith).toEqual({
      code: WS_CLOSE.TRY_AGAIN,
      reason: 'server full',
    });
  });
});
