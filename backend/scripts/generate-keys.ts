import fs from 'node:fs';
import path from 'node:path';
import { generateEd25519KeyPair } from '../src/security/keys.js';

function run() {
  console.log('--- Border-AI Ed25519 Key Generation ---');
  const pair = generateEd25519KeyPair();

  const outDir = process.cwd();
  const privKeyPath = path.join(outDir, 'jwt_ed25519_private.pem');

  fs.writeFileSync(privKeyPath, pair.privateKeyPem, { mode: 0o600 });
  console.log(`Private key written to: ${privKeyPath} (mode 0600)`);
  console.log(`Key ID (kid): ${pair.kid}`);
  console.log('\nPublic JWK representation:');
  console.log(JSON.stringify(pair.jwk, null, 2));

  console.log('\nEnvironment variables to add to your .env file:');
  console.log(`JWT_KID=${pair.kid}`);
  console.log(`JWT_PRIVATE_KEY_FILE=${privKeyPath}`);
  console.log('--- Key Generation Complete ---');
}

run();
