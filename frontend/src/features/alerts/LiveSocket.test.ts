import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LiveSocket } from './LiveSocket';
import { makeAlertView } from '@border-ai/protocol';

class FakeBrowserWebSocket {
  readyState = 0; // CONNECTING
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  closedWith?: { code: number; reason: string };

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = 1; // OPEN
      this.onopen?.();
    }, 0);
  }

  simulateMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateRaw(raw: string) {
    this.onmessage?.({ data: raw });
  }

  close(code = 1000, reason = '') {
    this.readyState = 3; // CLOSED
    this.closedWith = { code, reason };
    this.onclose?.();
  }
}

describe('Frontend LiveSocket Unit Tests', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('connects, receives hello message, updates status to open and triggers onResync(connected)', () => {
    const onStatus = vi.fn();
    const onMessage = vi.fn();
    const onResync = vi.fn();
    let currentSocket: FakeBrowserWebSocket | null = null;

    const socket = new LiveSocket({
      url: 'ws://localhost:4000/api/ws',
      WS: class extends FakeBrowserWebSocket {
        constructor(url: string) {
          super(url);
          currentSocket = this;
        }
      } as unknown as typeof WebSocket,
      onStatus,
      onMessage,
      onResync,
    });

    socket.start();
    expect(onStatus).toHaveBeenCalledWith('connecting');

    vi.advanceTimersByTime(10); // open event fires

    currentSocket?.simulateMessage({
      v: 1,
      type: 'hello',
      server_epoch: 'epoch-111',
      seq: 10,
      server_time: '2026-10-27T12:00:00.000Z',
    });

    expect(onStatus).toHaveBeenCalledWith('open');
    expect(onResync).toHaveBeenCalledWith('connected');
    expect(socket.getEpoch()).toBe('epoch-111');
    expect(socket.getSeq()).toBe(10);

    socket.stop();
  });

  it('triggers onResync(epoch_changed) when server epoch changes on reconnect', () => {
    const onResync = vi.fn();
    let currentSocket: FakeBrowserWebSocket | null = null;

    const socket = new LiveSocket({
      url: 'ws://localhost:4000/api/ws',
      WS: class extends FakeBrowserWebSocket {
        constructor(url: string) {
          super(url);
          currentSocket = this;
        }
      } as unknown as typeof WebSocket,
      onStatus: vi.fn(),
      onMessage: vi.fn(),
      onResync,
    });

    socket.start();
    vi.advanceTimersByTime(10);

    currentSocket?.simulateMessage({
      v: 1,
      type: 'hello',
      server_epoch: 'epoch-1',
      seq: 1,
      server_time: '2026-10-27T12:00:00.000Z',
    });
    expect(onResync).toHaveBeenCalledWith('connected');

    // Simulate server restart with new epoch
    currentSocket?.simulateMessage({
      v: 1,
      type: 'hello',
      server_epoch: 'epoch-2',
      seq: 0,
      server_time: '2026-10-27T12:05:00.000Z',
    });

    expect(onResync).toHaveBeenCalledWith('epoch_changed');
    socket.stop();
  });

  it('delivers sequential alert message without gap', () => {
    const onMessage = vi.fn();
    const onResync = vi.fn();
    let currentSocket: FakeBrowserWebSocket | null = null;

    const socket = new LiveSocket({
      url: 'ws://localhost:4000/api/ws',
      WS: class extends FakeBrowserWebSocket {
        constructor(url: string) {
          super(url);
          currentSocket = this;
        }
      } as unknown as typeof WebSocket,
      onStatus: vi.fn(),
      onMessage,
      onResync,
    });

    socket.start();
    vi.advanceTimersByTime(10);

    currentSocket?.simulateMessage({
      v: 1,
      type: 'hello',
      server_epoch: 'epoch-1',
      seq: 5,
      server_time: '2026-10-27T12:00:00.000Z',
    });

    const alert = makeAlertView();
    currentSocket?.simulateMessage({
      v: 1,
      type: 'alert.created',
      seq: 6, // Next sequential
      data: { alert },
    });

    expect(onMessage).toHaveBeenCalledTimes(1);
    expect(onResync).toHaveBeenCalledTimes(1); // Only initial 'connected'
    expect(socket.getSeq()).toBe(6);

    socket.stop();
  });

  it('detects skipped seq gap, delivers message, and triggers onResync(gap)', () => {
    const onMessage = vi.fn();
    const onResync = vi.fn();
    let currentSocket: FakeBrowserWebSocket | null = null;

    const socket = new LiveSocket({
      url: 'ws://localhost:4000/api/ws',
      WS: class extends FakeBrowserWebSocket {
        constructor(url: string) {
          super(url);
          currentSocket = this;
        }
      } as unknown as typeof WebSocket,
      onStatus: vi.fn(),
      onMessage,
      onResync,
    });

    socket.start();
    vi.advanceTimersByTime(10);

    currentSocket?.simulateMessage({
      v: 1,
      type: 'hello',
      server_epoch: 'epoch-1',
      seq: 5,
      server_time: '2026-10-27T12:00:00.000Z',
    });

    const alert = makeAlertView();
    currentSocket?.simulateMessage({
      v: 1,
      type: 'alert.created',
      seq: 8, // Skipped 6 and 7!
      data: { alert },
    });

    expect(onMessage).toHaveBeenCalledTimes(1);
    expect(onResync).toHaveBeenCalledWith('gap');
    expect(socket.getSeq()).toBe(8);

    socket.stop();
  });

  it('safely ignores unknown message types and malformed JSON without crashing', () => {
    const onMessage = vi.fn();
    let currentSocket: FakeBrowserWebSocket | null = null;

    const socket = new LiveSocket({
      url: 'ws://localhost:4000/api/ws',
      WS: class extends FakeBrowserWebSocket {
        constructor(url: string) {
          super(url);
          currentSocket = this;
        }
      } as unknown as typeof WebSocket,
      onStatus: vi.fn(),
      onMessage,
      onResync: vi.fn(),
    });

    socket.start();
    vi.advanceTimersByTime(10);

    currentSocket?.simulateRaw('{ bad json');
    currentSocket?.simulateMessage({ v: 1, type: 'future_event_type', seq: 99 });

    expect(onMessage).not.toHaveBeenCalled();
    socket.stop();
  });

  it('reconnects with exponential backoff on close', () => {
    const onStatus = vi.fn();
    let connectCount = 0;
    let currentSocket: FakeBrowserWebSocket | null = null;

    const socket = new LiveSocket({
      url: 'ws://localhost:4000/api/ws',
      WS: class extends FakeBrowserWebSocket {
        constructor(url: string) {
          super(url);
          connectCount += 1;
          currentSocket = this;
        }
      } as unknown as typeof WebSocket,
      onStatus,
      onMessage: vi.fn(),
      onResync: vi.fn(),
    });

    socket.start();
    vi.advanceTimersByTime(10);
    expect(connectCount).toBe(1);

    // Simulate unexpected server disconnect
    currentSocket?.close(1006);
    expect(onStatus).toHaveBeenCalledWith('closed');

    // Advance through backoff delay
    vi.advanceTimersByTime(2000);
    expect(connectCount).toBe(2);

    socket.stop();
  });
});
