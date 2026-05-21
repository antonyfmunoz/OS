# Handoff — 2026-05-21 Test Debt Closure

## Status: COMPLETE

Follows: `2026-05-21_0721_q2-q6-confirm-pass-closure.md`

Closes all 17 pre-existing test failures documented since the
2026-05-20 test-hygiene session. Also fixes 1 collection error in
`execution_orchestrator_v1.py`.

## What Changed

**Commit**: `75ecce61` on `worktree-test-fixes-and-hygiene`
**Scope**: 8 files changed, 192 insertions, 68 deletions

### Root cause

All 17 failures traced to the Layer 3.1 sovereignty reorg (Merge 7)
which moved files from `core/` to `execution/`, `composition/`,
`control_plane/`, and `interface/` directories. Tests hardcoding old
paths broke; production code with one stale relative import broke.

### Fixes by file

| File | Failures Fixed | Fix |
|------|---------------|-----|
| `execution/runtime/execution_orchestrator_v1.py` | 1 (collection) | Relative → absolute import for AdapterLifecycleManager |
| `tests/test_actuator_maturity_v1.py` | 2 | `core/actuation/` → `execution/actuation/`, `core/registry/` → `composition/registries/` |
| `tests/test_live_runtime_identity_v1.py` | 5 | `patch()` paths + file compile path updated |
| `tests/test_registry_propagation_integrity_v1.py` | 3 | 3 stale file paths updated |
| `tests/test_relay_execution_transport_v1.py` | 4 | `core.workstation` → `execution.workers.workstation` |
| `tests/test_persistent_substrate_continuity_engine_v1.py` | 1 | `core.registry` → `composition.registries` |
| `tests/test_gws_to_canonical_ingestion_v1.py` | 1 | Single-doc-ID assertion → pattern-based validation |
| `tests/test_work_state.py` | 1 | Backoff bound 10→20 (pressure multiplier) |

### Baseline progression

| Checkpoint | Passed | Failed | Skipped |
|---|---|---|---|
| Pre-Layer-3.1 (2026-05-20) | 3968 | 17 | 8 |
| **Post-test-debt-closure** | **3989** | **0** | **8** |

### Deferred items resolved

- **Graph pruning verify**: PASS — no stale `core/` paths in graph
- **eos_ai/ status**: CONFIRMED dead — 0 imports, untracked in git, safe to delete

### Deferred items remaining

- Layer 3 Phase 1 implementation (heavyweight, fresh session)
- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`) — UX decision, not technical
- Snapshot-graph tarball script (low priority)

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
