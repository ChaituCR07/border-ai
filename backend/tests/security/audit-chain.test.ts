import { describe, it, expect } from 'vitest';
import {
  canonicalJson,
  computeAuditHash,
  verifyAuditChain,
  GENESIS_HASH,
  InMemoryChainedAuditRepo,
  type AuditRecord,
} from '../../src/security/audit-chain.js';

describe('Tamper-Evident Hash-Chained Audit Log', () => {
  describe('canonicalJson', () => {
    it('produces identical output regardless of object key order', () => {
      const obj1 = { b: 2, a: 1, c: { z: 'last', y: 'first' } };
      const obj2 = { a: 1, c: { y: 'first', z: 'last' }, b: 2 };
      expect(canonicalJson(obj1)).toBe(canonicalJson(obj2));
      expect(canonicalJson(obj1)).toBe('{"a":1,"b":2,"c":{"y":"first","z":"last"}}');
    });

    it('handles primitives, arrays, and null', () => {
      expect(canonicalJson(null)).toBe('null');
      expect(canonicalJson('hello')).toBe('"hello"');
      expect(canonicalJson(42)).toBe('42');
      expect(canonicalJson([3, 1, 2])).toBe('[3,1,2]');
    });
  });

  describe('computeAuditHash', () => {
    it('computes consistent SHA-256 digest', () => {
      const params = {
        prevHash: GENESIS_HASH,
        timestamp: '2026-11-13T23:00:00.000Z',
        actor: 'admin@border.local',
        action: 'camera.create',
        entityType: 'camera',
        entityId: 'cam-01',
        detail: { location: 'North Gate', fps: 30 },
      };
      const hash1 = computeAuditHash(params);
      const hash2 = computeAuditHash(params);
      expect(hash1).toBe(hash2);
      expect(hash1).toHaveLength(64);
    });
  });

  describe('verifyAuditChain', () => {
    it('validates an empty chain as valid', () => {
      const result = verifyAuditChain([]);
      expect(result.valid).toBe(true);
      expect(result.totalVerified).toBe(0);
    });

    it('validates a correctly chained sequence', async () => {
      const repo = new InMemoryChainedAuditRepo();

      await repo.record({
        actor: 'user1',
        action: 'user.login',
        entity_type: 'user',
        entity_id: 'u-1',
        detail: { ip: '127.0.0.1' },
      });

      await repo.record({
        actor: 'user1',
        action: 'camera.update',
        entity_type: 'camera',
        entity_id: 'cam-north',
        detail: { status: 'ONLINE' },
      });

      await repo.record({
        actor: 'admin',
        action: 'rule.create',
        entity_type: 'rule',
        entity_id: 'rule-speed',
        detail: { threshold: 45 },
      });

      const records = repo.getAllRecords();
      expect(records).toHaveLength(3);
      expect(records[0]?.prev_hash).toBe(GENESIS_HASH);
      expect(records[1]?.prev_hash).toBe(records[0]?.hash);
      expect(records[2]?.prev_hash).toBe(records[1]?.hash);

      const verification = verifyAuditChain(records);
      expect(verification.valid).toBe(true);
      expect(verification.totalVerified).toBe(3);
    });

    it('detects payload tampering in the middle of the chain', async () => {
      const repo = new InMemoryChainedAuditRepo();

      await repo.record({ actor: 'u1', action: 'act1', entity_type: 'e', entity_id: '1', detail: { val: 10 } });
      await repo.record({ actor: 'u2', action: 'act2', entity_type: 'e', entity_id: '2', detail: { val: 20 } });
      await repo.record({ actor: 'u3', action: 'act3', entity_type: 'e', entity_id: '3', detail: { val: 30 } });

      // Attacker secretly tampers with record 1
      repo.tamperRecord(1, { val: 9999 });

      const records = repo.getAllRecords();
      const verification = verifyAuditChain(records);

      expect(verification.valid).toBe(false);
      expect(verification.brokenAt).toBe(2);
      expect(verification.reason).toContain('Hash calculation mismatch');
    });

    it('detects record deletion / broken prev_hash links', async () => {
      const repo = new InMemoryChainedAuditRepo();

      await repo.record({ actor: 'u1', action: 'act1', entity_type: 'e', entity_id: '1' });
      await repo.record({ actor: 'u2', action: 'act2', entity_type: 'e', entity_id: '2' });
      await repo.record({ actor: 'u3', action: 'act3', entity_type: 'e', entity_id: '3' });

      // Attacker drops record 1 (index 1)
      const all = repo.getAllRecords();
      const tamperedChain = [all[0]!, all[2]!];

      const verification = verifyAuditChain(tamperedChain);
      expect(verification.valid).toBe(false);
      expect(verification.reason).toContain('prev_hash mismatch');
    });
  });
});
