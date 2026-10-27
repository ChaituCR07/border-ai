import type { WebSocket } from 'ws';
import { randomUUID } from 'node:crypto';
import { type ServerMessage, WS_CLOSE } from '@border-ai/protocol';

export interface Client {
  id: string;
  socket: WebSocket;
  alive: boolean;
  actor: { id: string };
  connectedAt: number;
}

export interface HubOptions {
  maxClients?: number;
  maxBufferedBytes?: number;
  heartbeatMs?: number;
  log?: {
    info(o: object, m?: string): void;
    warn(o: object, m?: string): void;
    error(o: object, m?: string): void;
  };
  now?: () => Date;
}

export class Hub {
  readonly epoch = randomUUID();
  private seq = 0;
  private clients = new Map<string, Client>();
  private timer?: NodeJS.Timeout;
  private readonly maxClients: number;
  private readonly maxBufferedBytes: number;
  private readonly heartbeatMs: number;
  private readonly log: Required<HubOptions>['log'];
  private readonly now: () => Date;

  constructor(options: HubOptions = {}) {
    this.maxClients = options.maxClients ?? 200;
    this.maxBufferedBytes = options.maxBufferedBytes ?? 1024 * 1024; // 1 MB
    this.heartbeatMs = options.heartbeatMs ?? 15_000;
    this.log = options.log ?? {
      info: () => {},
      warn: () => {},
      error: () => {},
    };
    this.now = options.now ?? (() => new Date());
  }

  get size(): number {
    return this.clients.size;
  }

  get currentSeq(): number {
    return this.seq;
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => this.tick(), this.heartbeatMs);
    if (this.timer.unref) this.timer.unref();
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
    for (const c of this.clients.values()) {
      try {
        c.socket.close(WS_CLOSE.GOING_AWAY, 'server shutdown');
      } catch {
        // Ignore errors during mass closing
      }
    }
    this.clients.clear();
  }

  add(socket: WebSocket, actor: { id: string } = { id: 'anonymous' }): string | null {
    if (this.clients.size >= this.maxClients) {
      try {
        socket.close(WS_CLOSE.TRY_AGAIN, 'server full');
      } catch {
        // Ignore
      }
      return null;
    }

    const clientId = randomUUID();
    const client: Client = {
      id: clientId,
      socket,
      alive: true,
      actor,
      connectedAt: Date.now(),
    };

    this.clients.set(clientId, client);

    socket.on('pong', () => {
      client.alive = true;
    });

    socket.on('close', () => {
      this.clients.delete(clientId);
    });

    socket.on('error', () => {
      this.clients.delete(clientId);
    });

    // Send hello message immediately
    this.sendTo(client, {
      v: 1,
      type: 'hello',
      server_epoch: this.epoch,
      seq: this.seq,
      server_time: this.iso(),
    });

    return clientId;
  }

  /**
   * Broadcast state-changing events (alert.created, alert.updated, resync_required).
   * Monotonically increments seq by 1.
   */
  broadcastState(
    message: Omit<
      Extract<ServerMessage, { type: 'alert.created' | 'alert.updated' | 'resync_required' }>,
      'seq'
    >
  ): void {
    this.seq += 1;
    const fullMessage = { ...message, seq: this.seq } as ServerMessage;
    this.broadcast(fullMessage);
  }

  broadcast(message: ServerMessage): void {
    const data = JSON.stringify(message);
    for (const client of Array.from(this.clients.values())) {
      this.sendRaw(client, data);
    }
  }

  private sendTo(client: Client, message: ServerMessage): void {
    this.sendRaw(client, JSON.stringify(message));
  }

  private sendRaw(client: Client, data: string): void {
    const s = client.socket;
    // 1 === WebSocket.OPEN
    if (s.readyState !== 1) return;

    if (s.bufferedAmount > this.maxBufferedBytes) {
      this.log.warn(
        { client: client.id, buffered: s.bufferedAmount, max: this.maxBufferedBytes },
        'closing slow ws client'
      );
      try {
        s.close(WS_CLOSE.TRY_AGAIN, 'slow consumer');
      } catch {
        // Ignore close error
      }
      this.clients.delete(client.id);
      return;
    }

    try {
      s.send(data);
    } catch (err) {
      this.log.warn({ err, client: client.id }, 'failed to send to ws client');
      this.clients.delete(client.id);
    }
  }

  tick(): void {
    const clients = Array.from(this.clients.values());
    for (const c of clients) {
      if (!c.alive) {
        try {
          c.socket.terminate();
        } catch {
          // Ignore
        }
        this.clients.delete(c.id);
        continue;
      }

      c.alive = false;
      try {
        c.socket.ping();
      } catch {
        // Socket may have disconnected
        this.clients.delete(c.id);
      }
    }

    // Broadcast app-level heartbeat visible to browser clients
    this.broadcast({
      v: 1,
      type: 'heartbeat',
      seq: this.seq,
      server_time: this.iso(),
    });
  }

  private iso(): string {
    return this.now().toISOString();
  }
}
