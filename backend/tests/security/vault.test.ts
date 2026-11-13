import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import {
  sealCredential,
  openCredential,
  setVaultMasterKeyForTest,
  getVaultMasterKey,
} from '../../src/security/vault.js';

describe('AES-256-GCM Camera Credential Vault', () => {
  const fixturePath = path.resolve(__dirname, '../../../docs/fixtures/vault_vectors.json');
  const fixtureData = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  const testMasterKey = Buffer.from(fixtureData.key_hex, 'hex');

  it('decrypts cross-language test vectors from docs/fixtures/vault_vectors.json', () => {
    for (const vec of fixtureData.vectors) {
      const envelope = {
        key_id: fixtureData.key_id,
        nonce: vec.nonce_base64,
        ct: vec.ct_base64,
        tag: vec.tag_base64,
      };

      const decrypted = openCredential(vec.camera_id, envelope, testMasterKey);
      expect(decrypted).toBe(vec.plaintext);
    }
  });

  it('performs seal and open roundtrip with ephemeral key', () => {
    const cameraId = 'cam-gate-99';
    const secret = 'rtsp://operator:SecretP@ss2026@10.0.0.50/live';

    const envelope = sealCredential(cameraId, secret, { key: testMasterKey });
    expect(envelope.key_id).toBe('vault-2026-v1');
    expect(envelope.nonce).toBeDefined();
    expect(envelope.ct).toBeDefined();
    expect(envelope.tag).toBeDefined();

    const opened = openCredential(cameraId, envelope, testMasterKey);
    expect(opened).toBe(secret);
  });

  it('rejects decryption when ciphertext is tampered', () => {
    const vec = fixtureData.vectors[0];
    const tamperedCt = (vec.ct_base64[0] === 'A' ? 'B' : 'A') + vec.ct_base64.slice(1);
    const envelope = {
      key_id: fixtureData.key_id,
      nonce: vec.nonce_base64,
      ct: tamperedCt,
      tag: vec.tag_base64,
    };

    expect(() => {
      openCredential(vec.camera_id, envelope, testMasterKey);
    }).toThrow(/Vault authentication or decryption failed/);
  });

  it('rejects decryption when AAD (camera_id) does not match', () => {
    const vec = fixtureData.vectors[0];
    const envelope = {
      key_id: fixtureData.key_id,
      nonce: vec.nonce_base64,
      ct: vec.ct_base64,
      tag: vec.tag_base64,
    };

    // Stolen credential from cam-north-gate-01 injected into attacker-controlled cam-rogue-01
    expect(() => {
      openCredential('cam-rogue-01', envelope, testMasterKey);
    }).toThrow(/Vault authentication or decryption failed/);
  });

  it('rejects invalid nonce or tag length', () => {
    expect(() => {
      openCredential('cam-01', {
        key_id: 'k1',
        nonce: Buffer.from('short').toString('base64'),
        ct: Buffer.from('data').toString('base64'),
        tag: Buffer.from('16bytesauth_tag!').toString('base64'),
      }, testMasterKey);
    }).toThrow(/Invalid nonce length/);
  });
});
