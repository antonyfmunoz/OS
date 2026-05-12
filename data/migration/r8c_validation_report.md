# R8c Validation Report — Internal Topology Migration

> Generated: 2026-05-10
> Wave: R8c — Internal Runtime Self-Reference Migration

---

## Summary

| Metric | Pre-R8c | Post-R8c | Status |
|--------|---------|----------|--------|
| Files modified | — | 401 runtime/ + 1 test | — |
| Import rewrites | 1,431 `from eos_ai.` + 2 `import eos_ai.` | All → `runtime.*` | COMPLETE |
| String reference rewrites | 33 | All → `runtime.*` | COMPLETE |
| .env path rewrites | 38 | All → `runtime/.env` | COMPLETE |
| Comment/docstring updates | ~40 | Updated to canonical paths | COMPLETE |
| Test baseline | 8684/2691/495 | 8684/2691/495 | EXACT MATCH |
| Replay identity | 11/11 PASS | 11/11 PASS | EXACT MATCH |
| Cold boot | 0.105s | 0.105s | NO CHANGE |
| Cycle count | 0 visible (scanner blind) | 4 (full visibility) | EXPECTED |
| Cycle membership | N/A | Exact match with pre-R8b baseline | PASS |
| Module count | 455 | 455 | NO CHANGE |

## Internal Reference Rewrite Count

| Category | Count |
|----------|-------|
| `from eos_ai.X import Y` → `from runtime.X import Y` | 1,431 |
| `import eos_ai.X` → `import runtime.X` | 2 |
| String-based `"eos_ai.substrate.X"` → `"runtime.transport.X"` | 25 |
| String-based `"eos_ai.X"` → `"runtime.X"` | 8 |
| `load_dotenv('eos_ai', '.env')` → `('runtime', '.env')` | 18 |
| File path constants (`eos_ai/.substrate_*`) → `runtime/` | 6 |
| Comment/docstring module path refs | ~40 |
| **Total sites rewritten** | **~1,530** |

## Files Modified

401 files in `runtime/` modified:
- `runtime/substrate/` — 165 shim files (`eos_ai.transport.` → `runtime.transport.`)
- `runtime/transport/` — 114 files (internal cross-refs + string refs + paths)
- `runtime/*.py` — 122 top-level modules (import rewrites + .env paths + comments)

1 test file fixed:
- `tests/test_execution_adapter.py` — 5 mock.patch targets updated

## Circular Dependency Report

**Zero new circular dependencies introduced.**

| Metric | Pre-R8b (eos_ai/) | Post-R8c (runtime/) |
|--------|-------------------|---------------------|
| Cycle count | 4 | 4 |
| Cycle members | 79 | 79 |
| Cycle membership | — | EXACT MATCH (namespace-shifted) |

All 4 cycles are pre-existing and unchanged:
- Cycle 1: 2 modules
- Cycle 2: 6 modules
- Cycle 3: 2 modules
- Cycle 4: 69 modules

## Init Order Diff Report

**Module initialization order preserved.**

| Metric | Pre-R8c | Post-R8c |
|--------|---------|----------|
| Module-level imports visible | 20 | 504 |
| Lazy imports visible | 15 | 859 |
| Topological order | 455 modules | 455 modules |

The jump from 20→504 module-level imports is expected: before R8c, only
the 20 imports already using `runtime.*` were visible to the scanner.
After R8c, all 1,433 internal imports use `runtime.*` and are now visible.

The 504/859 counts exactly match the pre-R8b eos_ai/ baseline (504/859),
confirming the topology is structurally identical.

## Replay Equivalence Report

All 11 critical pairs verified `bridge_fn is canon_fn`:

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

## Remaining eos_ai.* Refs Inside runtime/

**1 reference remaining** — intentionally preserved:

```
runtime/transport/substrate_projection_boundaries.py:108:
    if "eos_ai/substrate/" in path_lower or "runtime/substrate/" in path_lower or "runtime/transport/" in path_lower:
```

This path-matching code correctly checks for both old (`eos_ai/substrate/`)
and new (`runtime/substrate/`, `runtime/transport/`) paths. Retaining the
old check is defensive — external callers may still pass old-style paths.

## Bridge Circularity Fixes

One mock.patch regression found and fixed:

| File | Old patch target | New patch target |
|------|-----------------|-----------------|
| `tests/test_execution_adapter.py` | `eos_ai.substrate.local_executor.execute_command` | `runtime.substrate.local_executor.execute_command` |
| `tests/test_execution_adapter.py` | `eos_ai.substrate.node_transport.send_task_via_http` | `runtime.substrate.node_transport.send_task_via_http` |
| `tests/test_execution_adapter.py` | `eos_ai.substrate.node_transport.check_http_health` | `runtime.substrate.node_transport.check_http_health` |

Root cause: R8c changed `runtime/transport/execution_adapter.py` to import
from `runtime.substrate` instead of `eos_ai.substrate`. The mock.patch
targets must match the module where the function is looked up at runtime.

## Rollback Command

```bash
git checkout HEAD -- runtime/ tests/test_execution_adapter.py
```

## R8d Readiness Assessment

**Status: READY**

R8c is complete. `runtime/` is now internally self-consistent:
- Zero `from eos_ai.*` imports inside `runtime/`
- Zero `"eos_ai.*"` string-based imports inside `runtime/`
- Full import graph visible (504 module-level, 859 lazy, 4 cycles — all pre-existing)
- All external bridges (`eos_ai/`) still functioning with replay identity verified

**R8d scope:** Replace temporary R8b bridges in `eos_ai/` with generated
permanent shims. Generate deterministically with manifest, diff report,
and orphan detection.

**R8d risk factors:**
- Medium risk — bridges are already working; R8d replaces them with a cleaner format
- Must preserve all external consumer compatibility
- Must generate shim manifest for ongoing maintenance
- Must detect orphan bridges (bridges with no external consumers)


---

> [Note: Test baseline re-anchored 2026-05-12. Actual collection is 11,532 / 338 (collected / collection errors). The 8684/2691/495 figures were valid at time of writing but are now stale. See data/audits/2026-05-12_ground_truth_audit.md §8.]
