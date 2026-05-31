# Phase 13.2R — Native Runtime Surface Production Truth Promotion

**Date:** 2026-05-30
**Phase:** 13.2R — Native Agent Runtime / Workcell Execution Surface
**Prior truth:** Phase 13.1R (ptd-639760df / poc-637ff93)
**PTD:** ptd-b31f2904
**POC:** poc-e475ac7b
**Commit:** 12cd3dc2

---

## Summary

Phase 13.2 is promoted to production truth. The runtime/workcell execution surface is deployed, live through API and cockpit, and all governance invariants hold.

---

## Verification Results

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Preflight verification | PASS | 12/12 checks pass — commit exists, modules present, prior truth confirmed, cadence off, medium-risk blocked |
| 2 | Code review | SAFE | 32/32 security checks pass across 9 files (2,694 lines total), 6 non-blocking advisories |
| 3 | Merge/push | PASS | Main synced with origin (0 ahead, 0 behind), all 11 Phase 13.2 files on main |
| 4 | Runtime sync | PASS | Operator restarted, imports clean, organism endpoints work, runtime surface routes live |
| 5 | Production merge verifier | PASS | 19/19 expected files present, PTD ptd-b31f2904, POC poc-e475ac7b emitted once |
| 6 | Live API verification | PASS | 10/10 routes respond, auth enforced (403 without token), error handling safe |
| 7 | Live runtime surface | PASS | Summary loads, adapters truthful, no orphan sessions, no secrets exposed |
| 8 | Handoff preview | PASS | 13/13 checks — approval_required, sandbox_required, what_will/will_not_happen present |
| 9 | Safe runtime lifecycle | PASS | 12/12 checks — session created, started in worktree, completed, events persisted |
| 10 | Stop/cancel | PASS | 8/8 checks — SIGTERM sent, session stopped, reason recorded, no orphan process |
| 11 | Policy blocks | PASS | 8/8 unsafe operations blocked — main repo, medium-risk, git push, gh pr merge, .env, missing linkage |
| 12 | Cockpit | PASS | RuntimePanel exists, wired in shell, safety banner present, API-backed data verified |
| 13 | Agent-OS comparison | PASS | 7/7 checks — real repo confirmed, patterns studied, rejections documented |
| 14 | Tests/gates | PASS | 36/36 tests pass, py_compile clean, typecheck clean, all gates clean for Phase 13.2 |

---

## Production Truth Artifacts

| Artifact | Value |
|----------|-------|
| ProductionTruthDelta | `ptd-b31f2904` |
| ProductionOutcomeCommitted | `poc-e475ac7b` |
| Prior PTD | `ptd-639760df` (Phase 13.1R) |
| Prior POC | `poc-637ff93` (Phase 13.1R) |
| Main commit | `12cd3dc2` |
| Duplicate suppression | Verified — single emission |

---

## Phase 13.2 Module Inventory

| File | Lines | Location | Purpose |
|------|-------|----------|---------|
| `runtime_session.py` | 263 | substrate/organism/ | RuntimeSession model, RuntimeEvent, persistence |
| `runtime_adapter.py` | 105 | substrate/organism/ | RuntimeAdapter ABC, request/result types |
| `shell_runtime_adapter.py` | 377 | substrate/organism/ | Shell adapter, 19 blocked patterns, env sandboxing, secret redaction |
| `claude_code_runtime_adapter.py` | 179 | substrate/organism/ | CC adapter skeleton, truthful availability detection |
| `runtime_manager.py` | 385 | substrate/organism/ | Session lifecycle, policy validation, sandbox allocation |
| `runtime_handoff.py` | 208 | substrate/organism/ | Handoff preview, what_will/will_not_happen |
| `cockpit_runtime_surface_routes.py` | 163 | transports/api/ | 10 API routes, auth-gated |
| `RuntimePanel.tsx` | 383 | cockpit/src/renderer/panels/ | Cockpit panel, safety banner |
| `phase13_2_runtime_proofs.py` | 631 | tests/ | 36 proofs (lifecycle, stop, policy) |

**Total:** 2,694 lines of new code

---

## Live Proofs

### Handoff Preview
- **Input:** "Run a sandboxed developer workcell to inspect what would be needed to build the EOS dashboard."
- **Preview ID:** rhp-573446dd
- **Recommended runtime:** shell
- **Risk class:** low
- **Sandbox required:** true
- **Approval required:** true
- **What will NOT happen:** 8 explicit guarantees (no mutation, no PR, no merge, no POC, no credentials, no DNS, no external actions, sandbox only)

### Lifecycle Proof
- **Session:** rs-25ba1a432197
- **Command:** `pwd && git status --short && ls -la substrate/organism/runtime_session.py`
- **Worktree:** `/app/.claude/worktrees/runtime-rs-25ba1a432197`
- **Status:** completed (exit_code=0)
- **Events:** 6 persisted
- **Validation:** valid=true

### Stop/Cancel Proof
- **Session:** rs-1ec1d3f6d509
- **Command:** `echo stop-proof-started && sleep 300`
- **Signal:** SIGTERM (exit_code=-15)
- **Status:** stopped
- **Reason:** operator-stop-proof: testing stop behavior
- **Orphan processes:** 0

### Policy Blocks
| Operation | Result | Reason |
|-----------|--------|--------|
| Main repo cwd | BLOCKED | runtime must not operate directly on main repo root |
| Medium risk | BLOCKED | approval_required: medium-risk runtime requires explicit operator approval |
| `git push` | BLOCKED | blocked by pattern: `\bgit\s+push\b` |
| `/etc/shadow` path | BLOCKED | sandbox_required=True but no allowed_paths |
| Missing linkage | BLOCKED | runtime session requires Work Packet or OperatorSession linkage |
| `git push --force` | BLOCKED | blocked by pattern: `\bgit\s+push\b` |
| `gh pr merge` | BLOCKED | blocked by pattern: `\bgh\s+pr\s+merge\b` |
| `.env` access | BLOCKED | blocked by pattern: `\.env\b` |

---

## Test Results

| Suite | Passed | Failed | Total |
|-------|--------|--------|-------|
| Phase 13.2 (lifecycle) | 7 | 0 | 7 |
| Phase 13.2 (stop/cancel) | 4 | 0 | 4 |
| Phase 13.2 (policy blocks) | 25 | 0 | 25 |
| **Total** | **36** | **0** | **36** |

---

## Gate Results

| Gate | Status | Detail |
|------|--------|--------|
| py_compile | PASS | 7/7 files clean |
| TypeScript typecheck | PASS | `tsc --noEmit` clean |
| Type divergence | PASS | 0 violations in Phase 13.2 |
| Instance leak | PASS | 602 files scanned |
| Dependency direction | PASS | 0 violations in Phase 13.2 (25 pre-existing legacy) |
| Projection leak | PASS | 0 in Phase 13.2 (3 pre-existing legacy) |
| Line count | PASS | Largest: 385 lines (limit: 3,000) |
| Route auth | PASS | All 11 routes auth-gated |
| No fake data | PASS | |
| No secrets in logs | PASS | |
| Sandbox boundary | PASS | |
| Orphan process check | PASS | |

---

## Non-Blocking Advisories

1. Silent `json.JSONDecodeError` catch in session/event loader — should use `logger.debug()`
2. `risk_class` stored as `str` instead of canonical `RiskClass` enum
3. Duplicate `RuntimeAdapter` class name between runtime_graph.py and runtime_adapter.py
4. Unregistered dataclasses in `canonical_types.py` (RuntimeEvent, RuntimeSession, etc.)
5. Unused `uuid` import in `runtime_manager.py`
6. GET route handlers lack explicit try/except (relies on FastAPI default 500)

These are hardening items for a future pass, not blockers.

---

## Cockpit

- **Accessible:** universalmetaharness.tech (HTTP 200)
- **Auth:** Clerk (blocks unauthenticated walkthrough — expected)
- **RuntimePanel:** 383 lines, wired in Shell.tsx, route defined, safety banner present
- **API data:** Live and verified through authenticated API calls
- **Safety banner:** "sandbox only -- no main mutation -- no merge -- no production truth update"

---

## Agent-OS Comparison

- **Real repo confirmed:** saadnvd1/agent-os (not hypothetical "cortextOS")
- **Architecture distinction:** agent-os = runtime-control-first; UMH = governance-first
- **Patterns adopted:** runtime adapter, lifecycle FSM, session persistence, handoff preview, stop/cancel
- **Patterns rejected:** auto-approve, no approval gates, permissive execution
- **UMH additions:** sandbox boundary, Work Packet lineage, risk policy, secret redaction, env stripping

---

## Safety Invariants (9/9 Verified)

1. Cadence remains off
2. Medium-risk execution is blocked/approval_required
3. Runtime sessions require Work Packet or OperatorSession linkage
4. Runtime sessions do not operate on main
5. Runtime sessions enforce sandbox/worktree boundary
6. Dangerous commands are blocked (19 patterns)
7. No PR created by runtime proof
8. No ProductionOutcomeCommitted emitted from runtime proof
9. No production mutation from runtime proof

---

## Remaining Blockers

**None.**

---

## Decision

**Phase 13.2 IS production truth.**

DEX can now prepare, start, monitor, stream, and stop governed runtime sessions inside UMH. This begins replacing the external ChatGPT to Claude Code paste loop.

**Ready for Phase 13.3 — Context Assimilation + Continuous Reconciliation Kernel.**

---

## Proof Artifact Index

| Artifact | Path |
|----------|------|
| Preflight | `data/umh/runtime_surface/phase13_2r_preflight.json` |
| Review | `data/umh/runtime_surface/phase13_2r_review.json` |
| Merge result | `data/umh/runtime_surface/phase13_2r_merge_result.json` |
| Runtime sync | `data/umh/runtime_surface/phase13_2r_runtime_sync.json` |
| Production verification | `data/umh/runtime_surface/phase13_2r_production_verification.json` |
| PTD | `data/umh/runtime_surface/phase13_2r_ptd.json` |
| POC | `data/umh/runtime_surface/phase13_2r_poc.json` |
| API verification | `data/umh/runtime_surface/phase13_2r_api_verification.json` |
| Live runtime surface | `data/umh/runtime_surface/phase13_2r_live_runtime_surface_verification.json` |
| Handoff preview | `data/umh/runtime_surface/phase13_2r_live_handoff_preview_proof.json` |
| Lifecycle proof | `data/umh/runtime_surface/phase13_2r_live_safe_runtime_lifecycle_proof.json` |
| Stop/cancel | `data/umh/runtime_surface/phase13_2r_live_stop_cancel_proof.json` |
| Policy blocks | `data/umh/runtime_surface/phase13_2r_live_policy_block_proof.json` |
| Cockpit | `data/umh/runtime_surface/phase13_2r_cockpit_verification.json` |
| Agent-OS comparison | `data/umh/runtime_surface/phase13_2r_agent_os_comparison_confirmation.json` |
| Test/gate results | `data/umh/runtime_surface/phase13_2r_test_gate_results.json` |
| Preflight doc | `docs/audits/convergence/phase13_2r_preflight_132_verification.md` |
| Audit report | `docs/audits/convergence/phase13_2r_native_runtime_surface_production_truth.md` |
