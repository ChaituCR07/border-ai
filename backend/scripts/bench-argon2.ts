import { hashPassword, verifyPassword, setArgon2Params } from '../src/security/passwords.js';

async function benchmark() {
  console.log('--- Argon2id Parameter Benchmark ---');
  const samplePassword = 'CorrectHorseBatteryStaple123!';

  const configurations = [
    { name: 'Low (m=8MB, t=1, p=1)', memory: 8192, passes: 1, parallelism: 1 },
    { name: 'OWASP Baseline (m=19MB, t=2, p=1)', memory: 19456, passes: 2, parallelism: 1 },
    { name: 'Strong (m=32MB, t=3, p=1)', memory: 32768, passes: 3, parallelism: 1 },
  ];

  for (const config of configurations) {
    setArgon2Params({
      memory: config.memory,
      passes: config.passes,
      parallelism: config.parallelism,
      tagLength: 32,
    });

    const startHash = performance.now();
    const phc = await hashPassword(samplePassword);
    const hashTime = (performance.now() - startHash).toFixed(2);

    const startVerify = performance.now();
    const valid = await verifyPassword(phc, samplePassword);
    const verifyTime = (performance.now() - startVerify).toFixed(2);

    console.log(
      `${config.name.padEnd(38)} -> Hash: ${hashTime}ms | Verify: ${verifyTime}ms | Valid: ${valid}`
    );
  }

  console.log('--- Benchmark Complete ---');
}

benchmark().catch(console.error);
