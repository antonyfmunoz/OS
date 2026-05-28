# Phase 6.2 — Execution Spine Enforcement + Cockpit-Only Control Surface

**Date**: 2026-05-27
**Baseline commit**: c613e2ba (Phase 6.1)
**Branch**: worktree-anti-divergence-gate

## Summary

Phase 6.2 makes the GovernedExecutionSpine the mandatory mutation path for all
MEDIUM+ risk operations. SpineGuard enforces a 4-level graduated enforcement
ladder. All mutation control is gated behind operator-authenticated cockpit
endpoints. The MutationRegistry now covers 22 mutation types across all risk
levels.

## Deliverables

### 1. SpineGuard Enforcement Ladder

`substrate/organism/spine_guard.py` — rewritten from 2-mode to 4-mode.

| Mode | Behavior |
|------|----------|
| `OFF` | No enforcement. All direct mutations allowed. |
| `WARN` | Log violations + emit events. Never blocks. |
| `BLOCK_HIGH_RISK` | Block MEDIUM/HIGH/CRITICAL. Allow LOW. **Default.** |
| `ENFORCE_ALL` | Block everything. Only spine-routed mutations permitted. |

Key method: `check_direct_mutation(source, description, risk_level)` returns
`True` if the mutation was BLOCKED.

Events emitted: `spine_guard_violation` (warn), `spine_guard_blocked` (block).
Journal entries recorded for every violation regardless of mode.
Legacy `report_direct_mutation()` preserved for backward compatibility.

### 2. Mutation Registry — 22 Registered Specs

`substrate/organism/mutation_registry.py` — expanded from 10 to 22 specs.

**Phase 6.1 originals (10):**
log_rotation, container_restart, runtime_refresh, test_suite, graph_rebuild,
branch_cleanup, disk_cleanup, repo_health, docker_health, runtime_reconciliation

**Phase 6.2 additions (12):**
docker_exec, tmux_send, shell_execute, process_kill, git_mutate,
remote_node_exec, file_write, file_delete, soul_doc_write, session_launch,
deployment, credential_write

**Risk distribution:** 7 low, 5 medium, 6 high, 4 critical
**Approval required:** 12/22 specs (all high + critical, plus container_restart and file_delete)
**Blast radius coverage:** local_file(3), local_runtime(8), single_service(5), multi_service(2), cluster_wide(2), external(1)

### 3. Cockpit-Only Control Doctrine

`transports/api/cockpit.py` — 31 references to `_require_operator_role`, covering:

**Protected routes (require operator token):**
- POST `/approvals/{id}/approve`, `/approvals/{id}/deny`
- POST `/organism/maintenance/run`, `/organism/workloads/run`, `/organism/workloads/run-all`
- POST `/organism/control`, `/organism/recursion/kill`, `/organism/recursion/resume`
- POST `/organism/reconcile`, `/organism/handoff`, `/organism/parallel`
- POST `/execution/start`, `/execution/stop`, `/execution/pause`, `/execution/resume`
- POST `/pipeline/submit`, `/comms/send`, `/workflows/{id}/trigger`
- POST `/notifications/send`
- POST/DELETE `/loops/*` (start, stop, run-once, create, delete)
- PATCH `/settings`, `/governance`
- All spine router mutation routes (approve, reject, retry, mode change)

**Intentionally unprotected (signaling, not mutation):**
- POST `/organism/signal` — signal intake (processed through governance)
- POST `/dex/converse` — conversational AI endpoint
- POST `/entities/companies` — entity lookup (read-only semantics)
- POST `/products/refresh` — product data refresh (idempotent)
- POST `/feedback` — feedback intake
- POST `/agents/{id}/signal` — agent signal intake

### 4. Cockpit Router Split

`transports/api/cockpit_spine_router.py` — 333 lines, 19 routes.

Extracted all spine/journal/mutation/guard endpoints from cockpit.py to prevent
the 3000-line limit breach. Uses `configure()` pattern: cockpit.py passes shared
utilities (get_organism, check_rate_limit, require_operator_dep) at mount time.
No circular imports.

**Routes in spine router:**
- `/organism/spine` — status, pending, active, completed, lifecycle
- `/organism/spine/approve`, `/reject`, `/retry` — mutation lifecycle
- `/organism/journal` — status, recent, lifecycle, statistics
- `/organism/mutations` — registry listing, individual spec detail
- `/organism/spine-guard` — guard status, blocked violations, mode change
- `/organism/execution-doctrine` — unified control surface view
- `/organism/reliability` — reliability metrics rollup

cockpit.py after split: **2831 lines** (well under 3000 limit).

### 5. Test Coverage

**576 organism tests, all passing.**

Phase 6.2 test file: `substrate/organism/tests/test_phase62_spine_enforcement.py`
(799 lines, 55 tests across 7 test classes)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestSpineGuardEnforcementLadder | 15 | All 4 modes, transitions, events, journal, backward compat |
| TestProductionEnforcement | 5 | LOW executes, MEDIUM pends, MEDIUM+approval executes, HIGH blocked, endpoint reflection |
| TestMutationRegistryContracts | 14 | 22 builtins, risk/reversibility/timeout/blast/modes/description, approval invariants |
| TestReliabilityContracts | 10 | Verification pass/fail/exception, rollback success/failure, retry, idempotency, success rate |
| TestDaemonIntegration | 5 | Default mode, journal wired, 22 specs, mode change, execution_mode_manager |
| TestCockpitSpineRouter | 3 | Importable, 19 routes present, configure() exists |
| TestRiskClassification | 4 | OBSERVE=low, critical not AUTONOMOUS, EXTERNAL/CLUSTER_WIDE requires high+ |

Phase 6.1 tests: 51 tests, all passing (backward compatible after GuardMode.ENFORCE → ENFORCE_ALL).

## Gates Passed

| Gate | Status |
|------|--------|
| Type divergence (`check_type_divergence.py`) | CLEAN |
| Instance leak (`check_instance_leak.py`) | CLEAN |
| Dependency direction (substrate/ → outward) | CLEAN (test files exempt) |
| py_compile all modified files | CLEAN |
| No file > 3000 lines | CLEAN (cockpit.py = 2831) |
| Full organism test suite | 576/576 PASSED |

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `substrate/organism/spine_guard.py` | 240 | Rewritten: 4-mode ladder, risk-based blocking, journal+event integration |
| `substrate/organism/mutation_registry.py` | 461 | 12 new MutationSpecs (22 total) |
| `substrate/organism/daemon.py` | 680 | SpineGuard wired with BLOCK_HIGH_RISK default |
| `transports/api/cockpit.py` | 2831 | Operator auth on 31 routes, spine routes extracted |
| `transports/api/cockpit_spine_router.py` | 333 | NEW — extracted spine/journal/mutation/guard routes |
| `substrate/organism/tests/test_phase62_spine_enforcement.py` | 799 | NEW — 55 enforcement tests |
| `substrate/organism/tests/test_phase61_governed_spine.py` | 686 | Updated for GuardMode.ENFORCE_ALL compat |

## Remaining Exceptions (with justification)

Direct mutation paths in the codebase (200+ call sites in workload_runner,
assisted_executor, maintenance_loop, etc.) are NOT individually refactored to
route through the spine. Instead:

1. **workload_runner.py** and **assisted_executor.py** already create ActionEnvelopes
   and submit through the GovernedExecutionSpine (Phase 6.1).
2. **SpineGuard** detects any bypass attempts at runtime and blocks MEDIUM+ risk.
3. **MutationRegistry** covers all 22 mutation categories — any new mutation type
   must be registered before the spine will accept it.

This is enforcement-by-detection, not enforcement-by-construction. The tradeoff:
lower refactoring risk now, with the guard as the safety net. Phase 6.3+ can
progressively convert direct callers to spine-routed paths.

## Next Highest-Leverage Step

**Phase 6.3: Autonomous execution gate.** With the spine enforcing and SpineGuard
blocking, the next step is wiring autonomous tick execution through the spine so
that the organism's self-directed mutations are also governed. Currently,
autonomous_tick.py delegates to workload_runner (which uses the spine), but
direct autonomous actions outside the workload system are not yet spine-gated.
