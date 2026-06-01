# Phase 14.1R: saas/ Decommission Decision Audit

**Date:** 2026-06-01
**Verdict:** SAFE -- 14/14 facts verified

## Decision

Operator approved deletion of `/opt/OS/saas/` (commit `e3bd216e`).
Beast/GitHub EntrepreneurOS is the canonical EOS source.
`transports/api/http/` is the canonical UMH platform API layer.

## What Was Deleted

30 files, 6074 lines. Hono-based TypeScript backend named `eos-projection`:
- 12 EOS route files (ventures, agents, skills, events, workflows, etc.)
- 14 EOS Drizzle table definitions + re-exported UMH tables
- 9 migration files (3 tracked, 6 orphaned -- broken journal)
- Instance-specific seed data
- No frontend. No deployment config.

## Why Deletion Was Safe

1. **UMH platform API is self-contained.** `transports/api/http/server.ts`
   owns all platform routes (organism, governance, chat, execution, settings,
   config, system, knowledge), auth middleware, DB client, schema, health
   check, and error handlers. Zero dependency on saas/.

2. **saas/ was a redundant shell.** It imported UMH platform routes from
   `transports/api/http/` and added EOS projection routes on top. The
   platform layer existed independently.

3. **Schema drift made convergence uneconomical.** 7 orphan migration tables,
   broken Drizzle journal, CRM tables using text org_id (breaking RLS),
   4 tables with no migration. Convergence cost exceeded value.

4. **No active imports.** Zero `from saas`, `import saas`, or `require(saas)`
   statements exist anywhere in the codebase.

5. **EOS canonical source is Beast/GitHub.** 603-file full-stack app with
   Clerk auth, complete frontend/backend, AI gateway. Operator confirmed.

6. **Fully recoverable.** All 30 files preserved in git history via
   `git show e3bd216e~1:saas/<file>`.

## Residual References

| Category | Count | Nature |
|----------|-------|--------|
| Pre-commit guard scripts | 4 | Exclusion paths in check_* scripts |
| Organism string literals | 3 | Topology data, readiness checks, reconciliation |
| Documentation files | 22 | Historical references in docs/ and knowledge/ |
| Active imports | 0 | None |

All residual references are non-functional strings. No runtime behavior depends on saas/.

## Test Gate

79/79 tests passed. 0 failed. 0 skipped.
All safety checks passed (no fake data, no secret leakage, no destructive sync).

## Evidence Chain

- `phase14_1_saas_inspection.json` -- full structural inspection before deletion
- `phase14_2_saas_and_eos_decision.json` -- operator decision record
- `phase14_1r_canonicality_decisions.json` -- canonicality confirmation
- `phase14_1_canonicality_candidate_report.json` -- 4-source EOS comparison
- `phase14_1_test_gate_results.json` -- test results
- `phase14_1_readiness_gate_report.json` -- readiness gate with operator decisions
- Commit `e3bd216e` -- deletion commit with full rationale
