import Redis from 'ioredis';

export type ConsumerState = 'idle' | 'running' | 'error';

export interface ConsumerLogger {
  info?(o: object, m?: string): void;
  warn(o: object, m?: string): void;
  error(o: object, m?: string): void;
}

export interface AlertStreamConsumerOptions {
  stream?: string;
  startId?: string;
  blockMs?: number;
  batchSize?: number;
  log?: ConsumerLogger;
  onResyncRequired?: (reason: string) => void;
}

export class AlertStreamConsumer {
  private lastId: string;
  private stopped = false;
  private redis: Redis;
  private readonly stream: string;
  private readonly blockMs: number;
  private readonly batchSize: number;
  private readonly log: ConsumerLogger;
  private readonly onResyncRequired?: (reason: string) => void;

  state: ConsumerState = 'idle';
  lastEntryAt: number | null = null;
  malformedCount = 0;

  constructor(
    baseRedis: Redis,
    private onEntry: (id: string, fields: Record<string, string>) => Promise<void> | void,
    options: AlertStreamConsumerOptions = {}
  ) {
    this.redis = baseRedis.duplicate();
    this.stream = options.stream ?? 'surveillance.alerts';
    this.lastId = options.startId ?? '$';
    this.blockMs = options.blockMs ?? 5000;
    this.batchSize = options.batchSize ?? 100;
    this.log = options.log ?? {
      warn: () => {},
      error: () => {},
    };
    this.onResyncRequired = options.onResyncRequired;
  }

  async run(): Promise<void> {
    this.state = 'running';
    let failures = 0;
    let hadError = false;

    while (!this.stopped) {
      try {
        // xread returns [ [ streamName, [ [ entryId, [ field1, val1, ... ] ], ... ] ] ]
        const res = await this.redis.xread(
          'COUNT',
          this.batchSize,
          'BLOCK',
          this.blockMs,
          'STREAMS',
          this.stream,
          this.lastId
        );

        if (hadError) {
          hadError = false;
          failures = 0;
          this.state = 'running';
          this.log.warn({ stream: this.stream }, 'alert stream consumer recovered from error');
          this.onResyncRequired?.('stream_recovered_after_outage');
        }

        if (!res) continue;

        for (const [, entries] of res as [string, [string, string[]][]][]) {
          for (const [id, flat] of entries) {
            // Crucial: advance lastId immediately so a poison message never wedges the loop
            this.lastId = id;
            this.lastEntryAt = Date.now();

            try {
              const fields = toObject(flat);
              await this.onEntry(id, fields);
            } catch (err) {
              this.malformedCount += 1;
              this.log.error({ err, id }, 'alert entry handler failed on stream entry');
            }
          }
        }
      } catch (err) {
        if (this.stopped) break;
        this.state = 'error';
        hadError = true;
        failures += 1;
        const delay = Math.min(15_000, 500 * Math.pow(2, failures));
        this.log.warn({ err, failures, delayMs: delay }, 'alert stream read error; retrying');
        await sleep(delay);
      }
    }
  }

  stop(): void {
    this.stopped = true;
    this.state = 'idle';
    try {
      this.redis.disconnect();
    } catch {
      // Ignore disconnect error on shutdown
    }
  }

  getLastId(): string {
    return this.lastId;
  }
}

function toObject(flat: string[]): Record<string, string> {
  const obj: Record<string, string> = {};
  for (let i = 0; i < flat.length; i += 2) {
    const k = flat[i];
    const v = flat[i + 1];
    if (k !== undefined && v !== undefined) {
      obj[k] = v;
    }
  }
  return obj;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
