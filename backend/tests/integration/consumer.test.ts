import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import Redis from 'ioredis';
import { AlertStreamConsumer } from '../../src/realtime/alert-stream-consumer.js';

describe('AlertStreamConsumer Integration Tests (Redis Streams)', () => {
  let redis: Redis;
  const testStream = `test:alerts:${Date.now()}`;

  beforeAll(() => {
    redis = new Redis('redis://localhost:6379/0');
  });

  afterAll(async () => {
    await redis.del(testStream);
    redis.disconnect();
  });

  it('tails stream and processes newly published alert entries', async () => {
    const received: Record<string, string>[] = [];
    const consumer = new AlertStreamConsumer(
      redis,
      (_id, fields) => {
        received.push(fields);
      },
      {
        stream: testStream,
        startId: '$',
        blockMs: 500,
      }
    );

    const runner = consumer.run();

    // Small delay to ensure XREAD is listening
    await new Promise((r) => setTimeout(r, 100));

    // XADD entry to stream
    const entryId = await redis.xadd(
      testStream,
      '*',
      'v', '1',
      'type', 'THREAT_ALERT',
      'alert_id', 'test-alert-1',
      'camera', 'CAM-01'
    );

    // Wait for consumer to process
    await new Promise((r) => setTimeout(r, 200));

    expect(received.length).toBe(1);
    expect(received[0]?.type).toBe('THREAT_ALERT');
    expect(received[0]?.alert_id).toBe('test-alert-1');
    expect(consumer.getLastId()).toBe(entryId);

    consumer.stop();
    await runner;
  });

  it('survives poison entry without crashing the consumer loop', async () => {
    let callCount = 0;
    const processed: string[] = [];

    const consumer = new AlertStreamConsumer(
      redis,
      (id, fields) => {
        callCount += 1;
        if (fields.alert_id === 'poison-alert') {
          throw new Error('Poison message simulation');
        }
        processed.push(fields.alert_id!);
      },
      {
        stream: testStream,
        startId: '$',
        blockMs: 500,
      }
    );

    const runner = consumer.run();
    await new Promise((r) => setTimeout(r, 100));

    // Add poison entry
    await redis.xadd(testStream, '*', 'alert_id', 'poison-alert');
    // Add valid entry immediately after
    await redis.xadd(testStream, '*', 'alert_id', 'healthy-alert-2');

    await new Promise((r) => setTimeout(r, 200));

    expect(callCount).toBe(2);
    expect(processed).toEqual(['healthy-alert-2']);
    expect(consumer.malformedCount).toBe(1);

    consumer.stop();
    await runner;
  });
});
