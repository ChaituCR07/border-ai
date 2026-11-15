# ADR 0053: Documentation Governance — Single Sources of Truth

## Status
Accepted

## Context
Across 28 days of rapid development, the Border-AI codebase has grown to span computer vision pipelines, multi-object tracking, ANPR, a Fastify backend, a React command center, Docker Compose topologies, and dozens of benchmark reports. 

Without strict governance, technical documentation drifts: accuracy numbers cited in the README diverge from actual test runs, OpenAPI documentation drifts from router schemas, RBAC permission tables desynchronize from authorization guards, and ADR decision logs fail to reflect all architecture shifts. 

To ensure the portfolio release is enterprise-grade and auditable, we must define single sources of truth for all quantitative claims and architecture documentation, enforced via automated CI freshness gates.

## Decision

1. **Single Sources of Truth Matrix:**
   - **Model & Performance Numbers:** Benchmark run summaries (`evaluation/runs/`, `perf/runs/`, `docs/perf/`, `docs/testing/`) are the sole sources of truth. The README Model Performance section must be rendered automatically or strictly validated against tagged run summaries.
   - **API Reference:** The OpenAPI 3.0 specification exported from Fastify router schemas (`backend/src/routes/`) is the sole truth. Static documentation is generated as Redoc HTML (`docs/api/index.html`).
   - **RBAC Matrix:** Fastify permission policies in `backend/src/auth/policy.ts` are the source of truth for role entitlements documented in `docs/security/rbac_matrix.md`.
   - **Architecture Decision Records:** The front-matter and headers in `docs/decisions/*.md` are indexed programmatically into `docs/decisions/README.md`.
   - **Database Schema:** PostgreSQL migration scripts (`001` through `008`) and live schema introspection determine database ERD documentation.
   - **Release Facts:** `docs/release/facts.md` gathers project-wide verification metrics (test counts, endpoints, migrations, lines of code) to prevent conflicting statistics across release documents.

2. **Automated Freshness & Claim Auditing:**
   - Extend `scripts/report/check_claims.py` to audit all public documentation.
   - Unbacked claims or banned marketing superlatives ("military-grade", "100% accurate", "unbreakable", "real-time" without context) trigger hard test failures.
   - Every quantitative performance metric must cite its corresponding run identifier (`[run:...]`).

## Consequences

- Documentation maintenance becomes programmatic, deterministic, and verifiable.
- All numbers published in the README, solution briefs, case studies, and video descriptions remain 100% synchronized.
- Zero risk of marketing hyperbole compromising engineering credibility.
