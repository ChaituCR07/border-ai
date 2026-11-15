# Border-AI Release Code Freeze Policy (v1.0.0)

## 1. Code Freeze Declaration

Effective as of **Day 28**, the Border-AI codebase is under formal **Feature Freeze & Code Freeze** for the `v1.0.0` Production Release.

---

## 2. Permitted Changes During Code Freeze

1. **Documentation Updates:**
   - Architectural diagrams, API reference generation, README updates, user manuals, and deployment runbooks.
2. **Critical Bug Fixes Only:**
   - Permitted strictly for regressions discovered during clean-clone deployment drills or documentation snippet verification.
   - Any bug fix requires:
     - An accompanying regression test.
     - An explicit line in `CHANGELOG.md`.
     - Code review and clean CI verification.
3. **Zero New Features:**
   - No architectural refactoring, new model additions, or new API routes may be introduced.
   - All proposed enhancements must be deferred to `docs/LIMITATIONS.md` or the `Future Work` roadmap.

---

## 3. Quality Assurance Release Checklist

Before tagging `v1.0.0`, all quality gates must pass:
- [x] All 280+ tests passing across unit, integration, and security suites.
- [x] Static Dockerfile and Compose validation clean (`docker compose config -q`).
- [x] Zero unencrypted canary secrets or token leaks detected (`compose_canary_scan.py`).
- [x] Single trailing newline `\n` verified across all repository files.
- [x] Working tree clean on `feature/final-documentation-and-demo-release`.
