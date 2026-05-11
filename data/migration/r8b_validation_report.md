# R8b Validation Report — Atomic Move + Bridge Installation

> Generated: 2026-05-10
> Wave: R8b — Create Canonical `runtime/` via Atomic Move

---

## Summary

| Metric | Value |
|--------|-------|
| Files moved to `runtime/` | 455 .py files |
| Bridge modules in `eos_ai/` | 458 (443 `import *` + 14 `sys.modules` + 1 `__init__.py`) |
| Test baseline pre-move | 8684 passed / 2691 failed / 495 errors |
| Test baseline post-move | 8684 passed / 2691 failed / 495 errors |
| Net regressions | **0** |
| Replay identity checks | 11/11 PASS |
| Cold boot (canonical) | 0.227s (baseline: 0.247s) |
| Cold boot (bridge) | 0.242s (baseline: 0.247s) |

## Moved Module Manifest

All 455 Python files from `eos_ai/` moved to `runtime/` via `git mv`:

- **Top-level modules:** 407 files (`eos_ai/*.py` → `runtime/*.py`)
- **transport/ subpackage:** 31 files (`eos_ai/transport/*.py` → `runtime/transport/*.py`)
- **substrate/ subpackage:** 10 files (`eos_ai/substrate/*.py` → `runtime/substrate/*.py`)
- **interfaces/ subpackage:** 5 files (`eos_ai/interfaces/*.py` → `runtime/interfaces/*.py`)
- **Depth-flattened:** 2 files (`eos_ai/runtime/work_state.py` → `runtime/work_state.py`, `eos_ai/runtime/provider_state.py` → `runtime/provider_state.py`)

Full manifest: `data/migration/r8b_bridge_manifest.json`

## Bridge Module Manifest

458 bridge modules installed in `eos_ai/`:

### Bridge types

| Type | Count | Pattern | Used when |
|------|-------|---------|-----------|
| `import *` | 443 | `from runtime.X import *` | Public names only |
| `sys.modules` | 14 | `sys.modules[__name__] = _mod` | Private names needed |
| Init re-export | 1 | `eos_ai/runtime/__init__.py` | Package init |

### sys.modules bridges (private name consumers)

- `eos_ai/goal_selector.py` → `runtime.goal_selector`
- `eos_ai/runtime/work_state.py` → `runtime.work_state`
- `eos_ai/runtime/provider_state.py` → `runtime.provider_state`
- `eos_ai/substrate/claude_session_bridge.py` → `runtime.transport.claude_session_bridge`
- `eos_ai/substrate/llm_planner.py` → `runtime.transport.llm_planner`
- `eos_ai/substrate/session_watcher.py` → `runtime.transport.session_watcher`
- `eos_ai/substrate/stt_producer.py` → `runtime.transport.stt_producer`
- `eos_ai/substrate/workflow_execution.py` → `runtime.transport.workflow_execution`
- `eos_ai/transport/claude_session_bridge.py` → `runtime.transport.claude_session_bridge`
- `eos_ai/transport/llm_planner.py` → `runtime.transport.llm_planner`
- `eos_ai/transport/session_watcher.py` → `runtime.transport.session_watcher`
- `eos_ai/transport/stt_producer.py` → `runtime.transport.stt_producer`
- `eos_ai/transport/work_order_contracts.py` → `runtime.transport.work_order_contracts`
- `eos_ai/transport/workflow_execution.py` → `runtime.transport.workflow_execution`

## Namespace Ownership Report

| Path | Owner | Content |
|------|-------|---------|
| `runtime/` | Canonical | 455 mutable Python source files |
| `eos_ai/` | Bridge-only | 458 re-export bridges (≤4 lines each) |
| `eos_ai/.env` | Symlink | → `../runtime/.env` |
| `core/runtime/` | Separate package | Unaffected (different Python path) |
| `infra/docker/` | Deployment | Relocated from old `runtime/` in R8a |

**Core invariant:** `runtime/` is the sole location with mutable implementation.
`eos_ai/` contains zero business logic — only re-export bridges.

## Import Graph Diff Report

Pre-move snapshot: `data/migration/r8b_pre_move_graph.json`
Post-move snapshot: `data/migration/r8b_post_move_graph.json`
Diff: `data/migration/r8b_graph_diff.json`

| Metric | Pre-move | Post-move | Note |
|--------|----------|-----------|------|
| Total modules | 455 | 455 | Match |
| Module-level imports | 504 | 17 | Expected: scanner filters by package_prefix |
| Lazy imports | 859 | 6 | Expected: internal refs still use `eos_ai.*` |
| Structural equivalence | — | PASS | All modules present after normalization |

## Cycle Diff Report

| Metric | Pre-move | Post-move |
|--------|----------|-----------|
| Cycle count | 4 | 0 |
| Cycle members | 79 | 0 |

Post-move cycle count drops to 0 because internal refs still use `eos_ai.*`
prefix (filtered out by scanner). True cycle analysis will be re-evaluated
after R8c rewrites all internal imports to `runtime.*`.

## Replay Equivalence Report

All 11 critical function/class pairs verified `bridge_fn is canon_fn`:

```
PASS: eos_ai.db.get_conn is runtime.db.get_conn
PASS: eos_ai.context.load_context_from_env is runtime.context.load_context_from_env
PASS: eos_ai.model_router.call_with_fallback is runtime.model_router.call_with_fallback
PASS: eos_ai.gateway.get_gateway is runtime.gateway.get_gateway
PASS: eos_ai.memory.AgentMemory is runtime.memory.AgentMemory
PASS: eos_ai.agent_runtime.AgentRuntime is runtime.agent_runtime.AgentRuntime
PASS: eos_ai.transport.storage.get_storage is runtime.transport.storage.get_storage
PASS: eos_ai.substrate.storage.get_storage is runtime.transport.storage.get_storage
PASS: eos_ai.runtime.work_state._measure_pressure is runtime.work_state._measure_pressure
PASS: eos_ai.goal_selector.GoalSelector is runtime.goal_selector.GoalSelector
PASS: eos_ai.runtime.provider_state.get_system_state is runtime.provider_state.get_system_state
```

## Internal Reference Fixes

The following `runtime/` files contained stale `eos_ai.runtime.*` or
`eos_ai.transport.*` references that caused circular bridge dependencies.
Fixed to use canonical `runtime.*` paths:

| File | Old import | New import |
|------|-----------|------------|
| `runtime/provider_state.py:249` | `from eos_ai.runtime.work_state` | `from runtime.work_state` |
| `runtime/orchestrator.py:1780` | `from eos_ai.runtime.work_state` | `from runtime.work_state` |
| `runtime/orchestrator.py:1799` | `from eos_ai.runtime.provider_state` | `from runtime.provider_state` |
| `runtime/cc_sdk.py:62,287` | `from eos_ai.runtime.provider_state` | `from runtime.provider_state` |
| `runtime/model_router.py:41,83,99` | `from eos_ai.runtime.provider_state` | `from runtime.provider_state` |
| `runtime/work_state.py:14` | `from eos_ai.runtime.work_state` (docstring) | `from runtime.work_state` |
| `runtime/transport/work_order_factory.py:14` | `from eos_ai.transport.work_order_contracts` | `from runtime.transport.work_order_contracts` |
| `runtime/research_engine.py:42` | `from eos_ai.strategy_engine` | `from runtime.strategy_engine` |
| `runtime/transport/pipeline_execution.py:318` | `from eos_ai.transport.task_execution` | `from runtime.transport.task_execution` |
| `runtime/transport/voice_eos_responder.py:130` | `from eos_ai.transport.claude_session_bridge` | `from runtime.transport.claude_session_bridge` |

## Test Fix

`tests/test_registry_propagation_integrity_v1.py`: 3 tests used
`Path(ROOT) / "eos_ai" / "interfaces" / ...` to read source. Updated to
read from `runtime/interfaces/` (canonical location).

## Rollback Command

```bash
git checkout HEAD -- eos_ai/ && rm -rf runtime/
```

## R8c Readiness Assessment

**Status: READY**

R8b is complete. The canonical `runtime/` namespace exists with:
- All 455 modules moved and importable
- 458 bridges maintaining backward compatibility
- Zero test regressions
- Replay identity verified

**R8c scope:** Rewrite 1,434 internal `from eos_ai.*` imports within
`runtime/` to use `runtime.*` paths. This makes `runtime/` internally
self-consistent and eliminates dependency on the bridge layer from within
the canonical source.

**R8c risk factors:**
- Highest risk wave — 1,434 import sites to rewrite
- Requires pre/post import graph comparison
- Must preserve cycle count and init order
- Cold boot timing must remain within bounds
