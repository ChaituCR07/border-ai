import { getPool } from '../src/common/db.js';
import { verifyAuditChain, type AuditRecord } from '../src/security/audit-chain.js';

async function main() {
  console.log('--- Border-AI Tamper-Evident Audit Chain Verifier ---');
  let pool;
  try {
    pool = getPool();
  } catch (err) {
    console.error('Failed to initialize database pool:', err);
    process.exit(1);
  }

  try {
    const res = await pool.query(
      `SELECT audit_id, at, actor, action, entity_type, entity_id, request_id,
              role, ip, user_agent_hash, prev_hash, hash, detail
       FROM api_audit_log
       WHERE prev_hash IS NOT NULL AND hash IS NOT NULL
       ORDER BY audit_id ASC`
    );

    const records: AuditRecord[] = res.rows.map((r) => ({
      audit_id: r.audit_id,
      at: new Date(r.at).toISOString(),
      actor: r.actor,
      action: r.action,
      entity_type: r.entity_type,
      entity_id: r.entity_id,
      request_id: r.request_id,
      role: r.role,
      ip: r.ip,
      user_agent_hash: r.user_agent_hash,
      prev_hash: r.prev_hash,
      hash: r.hash,
      detail: r.detail,
    }));

    if (records.length === 0) {
      console.log('No chained audit entries found in database. Chain is empty.');
      process.exit(0);
    }

    const result = verifyAuditChain(records);

    if (result.valid) {
      console.log(`[AUDIT INTEGRITY OK] Chain integrity verified across all ${result.totalVerified} entries.`);
      console.log(`Tip hash: ${records[records.length - 1]?.hash}`);
      process.exit(0);
    } else {
      console.error(`[AUDIT INTEGRITY BREACH] Broken link detected at sequence #${result.brokenAt}!`);
      console.error(`Reason: ${result.reason}`);
      console.error(`Expected Hash: ${result.expectedHash}`);
      console.error(`Actual Hash:   ${result.actualHash}`);
      process.exit(1);
    }
  } catch (err) {
    console.error('Audit verification query failed:', err);
    process.exit(1);
  } finally {
    await pool.end().catch(() => {});
  }
}

main();
