import { ServerMessage } from '@border-ai/protocol';
import { backoffMs } from '../video/backoff';

export type SocketStatus = 'connecting' | 'open' | 'closed';
export type ResyncReason = 'connected' | 'epoch_changed' | 'gap' | 'server_requested';

export type AlertMessage = Extract<ServerMessage, { type: 'alert.created' | 'alert.updated' }>;

export interface LiveSocketOptions {
  url: string;
  WS?: typeof WebSocket;
  watchdogMs?: number;
  onStatus: (status: SocketStatus) => void;
  onMessage: (message: AlertMessage) => void;
  onResync: (reason: ResyncReason) => void;
}

export class LiveSocket {
  private ws?: WebSocket;
  private attempt = 0;
  private retryTimer?: ReturnType<typeof setTimeout>;
  private watchdogTimer?: ReturnType<typeof setTimeout>;
  private epoch?: string;
  private seq?: number;
  private stopped = true;

  constructor(private readonly options: LiveSocketOptions) {}

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    this.clearTimers();
    this.detachSocket();
    if (this.ws) {
      try {
        this.ws.close(1000, 'client stopped');
      } catch {
        // Ignore close error on stopped socket
      }
      this.ws = undefined;
    }
    this.options.onStatus('closed');
  }

  getStatus(): SocketStatus {
    if (!this.ws) return 'closed';
    if (this.ws.readyState === 1) return 'open';
    if (this.ws.readyState === 0) return 'connecting';
    return 'closed';
  }

  getSeq(): number | undefined {
    return this.seq;
  }

  getEpoch(): string | undefined {
    return this.epoch;
  }

  private connect(): void {
    if (this.stopped) return;

    this.options.onStatus('connecting');
    const WebSocketClass = this.options.WS ?? WebSocket;

    try {
      const ws = new WebSocketClass(this.options.url);
      this.ws = ws;

      ws.onopen = () => {
        this.armWatchdog();
      };

      ws.onmessage = (event: MessageEvent) => {
        this.armWatchdog();
        this.handleMessage(event.data);
      };

      ws.onerror = () => {
        // onclose follows automatically per WebSocket spec
      };

      ws.onclose = () => {
        this.afterClose();
      };
    } catch {
      this.afterClose();
    }
  }

  private handleMessage(raw: unknown): void {
    let json: unknown;
    try {
      json = JSON.parse(String(raw));
    } catch {
      return; // Ignore malformed JSON
    }

    const parsed = ServerMessage.safeParse(json);
    if (!parsed.success) {
      return; // Ignore unknown message types for forward compatibility
    }

    const m = parsed.data;

    switch (m.type) {
      case 'hello': {
        const isEpochChange = this.epoch !== undefined && this.epoch !== m.server_epoch;
        const reason: ResyncReason = isEpochChange ? 'epoch_changed' : 'connected';

        this.epoch = m.server_epoch;
        this.seq = m.seq;
        this.attempt = 0; // Reset reconnection counter on verified connection

        this.options.onStatus('open');
        this.options.onResync(reason);
        return;
      }

      case 'heartbeat': {
        // If server heartbeat reports a sequence higher than known, missed alerts occurred
        if (this.seq !== undefined && m.seq > this.seq) {
          this.seq = m.seq;
          this.options.onResync('gap');
        }
        return;
      }

      case 'resync_required': {
        this.seq = m.seq;
        this.options.onResync('server_requested');
        return;
      }

      case 'alert.created':
      case 'alert.updated': {
        // Detect skipped sequence numbers
        const hasGap = this.seq !== undefined && m.seq !== this.seq + 1;
        this.seq = m.seq;

        this.options.onMessage(m);

        if (hasGap) {
          this.options.onResync('gap');
        }
        return;
      }
    }
  }

  private armWatchdog(): void {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
    }
    const timeoutMs = this.options.watchdogMs ?? 45_000;
    this.watchdogTimer = setTimeout(() => {
      // Silence threshold exceeded: forcefully drop connection and schedule backoff reconnect
      this.detachSocket();
      try {
        this.ws?.close();
      } catch {
        // Ignore
      }
      this.afterClose();
    }, timeoutMs);
  }

  private clearTimers(): void {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = undefined;
    }
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = undefined;
    }
  }

  private detachSocket(): void {
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
    }
  }

  private afterClose(): void {
    if (this.watchdogTimer) {
      clearTimeout(this.watchdogTimer);
      this.watchdogTimer = undefined;
    }

    this.options.onStatus('closed');

    if (this.stopped) return;

    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
    }

    const delayMs = backoffMs(this.attempt++);
    this.retryTimer = setTimeout(() => {
      this.connect();
    }, delayMs);
  }
}
