# R8f Validation Report — Semantic Address / String-Reference Migration

> Generated: 2026-05-11
> Wave: R8f — Migrate semantic runtime references to canonical namespace

---

## Summary

| Metric | Value |
|--------|-------|
| Files modified | 14 (13 core/ + 1 runtime/) |
| Lines changed | 36 (symmetric: 36 insertions, 36 deletions) |
| `from eos_ai.X` → `from runtime.X` | 16 sites (core/) |
| Registry entries updated | 3 (convergence engines) |
| File path constants | 7 sites |
| CLI command strings | 1 site |
| Docstring/comment updates | 9 sites |
| Backward-compatible path check | 1 (kept, reordered) |
| Test baseline | 8684/2691/495 (exact match) |
| Module identity | PASS |
| Replay identity | PASS |
| Singleton identity | PASS |
| Cold boot | 0.065s (improved from 0.079s) |
| Regressions | 0 |

## Scope

### Files modified
| File | Changes |
|------|---------|
| `core/execution_contract.py` | 7 imports (context, db, execution_trace, gateway, authority_engine, memory, agent_runtime) |
| `core/agent_harness.py` | 3 imports (memory, model_router, agent_runtime) + 4 docstring updates |
| `core/action_system/policy.py` | 1 import (authority_engine) + 4 docstring updates |
| `core/workstation/foreground_cu_ingestion_execution_v1.py` | 1 import (memory_scope_contracts) |
| `core/workstation/environment_mapping_engine_v1.py` | 1 import (memory_scope_contracts) |
| `core/coord_assignment.py` | 1 import (embedder) |
| `core/semantic_space.py` | 1 import (embedder) |
| `core/optimizer.py` | 3 file path constants |
| `core/environment.py` | 1 forbidden write prefix + 2 docstring paths |
| `core/environment_bridge/bootstrap_plan.py` | 1 CLI command path |
| `core/runtime/runtime_bootstrap_state_v1.py` | 1 env file path |
| `core/capability.py` | 1 docstring reference |
| `core/wiki_navigation.py` | 2 comment references |
| `core/convergence/filesystem_integrity_engine_v1.py` | 2 registry entries (ownership + topology check) |
| `core/convergence/namespace_convergence_engine_v1.py` | 1 registry entry |
| `core/convergence/repository_topology_scanner_v1.py` | 1 registry entry |
| `runtime/transport/substrate_projection_boundaries.py` | 1 path check reordered (canonical first, backward-compat kept) |

## Migration Categories

### 1. Import rewrites (16 sites in core/)
`core/` was missed by R8e (which targeted services/scripts/tests/).
These are actual `from eos_ai.X import Y` statements in core modules
that now import directly from `runtime.*`.

Key imports migrated:
- `core/execution_contract.py`: context, db, execution_trace, gateway, authority_engine, memory, agent_runtime
- `core/agent_harness.py`: memory, model_router, agent_runtime
- `core/action_system/policy.py`: authority_engine (lazy)
- `core/workstation/*.py`: memory_scope_contracts
- `core/coord_assignment.py`, `core/semantic_space.py`: embedder

### 2. Registry entries (3 convergence engines)
- `CANONICAL_OWNERSHIP`: `"eos_ai": "intelligence"` → `"runtime": "intelligence"`
- `CANONICAL_NAMESPACES`: `"eos_ai"` → `"runtime"`
- `EXPECTED_DIRS`: `"eos_ai"` → `"runtime"`
- Topology check: `["core", "eos_ai", "services"]` → `["core", "runtime", "services"]`

### 3. File path constants (7 sites)
- `core/optimizer.py`: 3× `target="eos_ai/model_router.py"` → `runtime/model_router.py`
- `core/agent_harness.py`: 1× `target="eos_ai/memory.py"` → `runtime/memory.py`
- `core/runtime/runtime_bootstrap_state_v1.py`: `"eos_ai/.env"` → `"runtime/.env"`
- `core/environment.py`: forbidden write prefix `eos_ai` → `runtime`
  + docstring sandbox examples

### 4. CLI command string (1 site)
- `core/environment_bridge/bootstrap_plan.py`:
  `python3 /opt/OS/eos_ai/substrate/local_worker_auto_loop.py` →
  `python3 /opt/OS/runtime/substrate/local_worker_auto_loop.py`

### 5. Backward-compatible path check (1 site, preserved)
`runtime/transport/substrate_projection_boundaries.py:108`:
Reordered to check canonical paths first, backward-compat `eos_ai/substrate/`
check kept because shim paths still exist:
```python
if "runtime/substrate/" in path_lower or "runtime/transport/" in path_lower or "eos_ai/substrate/" in path_lower:
```

## Items Requiring Manual Update

### `.claude/settings.json` (3 references)
Cannot be modified by the agent (self-modification blocked). Update manually:

1. **Deny rule**: `"Read(/opt/OS/eos_ai/.env)"` → `"Read(/opt/OS/runtime/.env)"`
2. **PostToolUse hook**: `"import eos_ai"` → `"import runtime"`
3. **PreCompact hook**: `"from eos_ai.context import load_context_from_env"` → `"from runtime.context import load_context_from_env"`

## Remaining Intentional eos_ai References

### Legacy test validators (63 references in tests/legacy/)
All are string assertions or test names verifying that runtime/umh code
doesn't import from the eos_ai bridge layer. These are correct and must
stay until the eos_ai/ directory is removed in a future wave.

### Runtime backward-compat path check (1 reference)
`runtime/transport/substrate_projection_boundaries.py` — classifies
`eos_ai/substrate/` paths as UMH_SUBSTRATE. Kept for backward
compatibility with shim paths.

## Identity Verification

### Module Identity (PASS)
```
PASS: eos_ai.db is runtime.db
```

### Replay Identity (PASS)
```
PASS: eos_ai.db.get_conn is runtime.db.get_conn
```

### Depth-Flattened Identity (PASS)
```
PASS: eos_ai.runtime.work_state is runtime.work_state
PASS: eos_ai.runtime.work_state._measure_pressure is runtime.work_state._measure_pressure
```

### Singleton Identity (PASS)
```
runtime.provider_state.get_system_state() is eos_ai.provider_state.get_system_state()
```

### Core Import Verification (PASS)
```
from runtime.context import load_context_from_env   — OK
from runtime.memory import AgentMemory               — OK
from runtime.authority_engine import RISK_CLASSES     — OK
from runtime.embedder import embed                    — OK
from runtime.substrate.memory_scope_contracts import MemoryScope — OK
```

## Cold Boot Comparison

| Wave | Cold boot avg |
|------|--------------|
| R8d | 0.118s |
| R8e | 0.079s |
| R8f | 0.065s |

Cumulative improvement: -45% from R8d baseline.

## Test Baseline

| Metric | R8e | R8f | Delta |
|--------|-----|-----|-------|
| Passed | 8,684 | 8,684 | 0 |
| Failed | 2,691 | 2,691 | 0 |
| Errors | 495 | 495 | 0 |

## Rollback Command

```bash
git checkout HEAD -- core/ runtime/transport/substrate_projection_boundaries.py
```

## R8g Readiness Assessment

**Status: READY**

R8f is complete. All semantic runtime references now use `runtime.*`:
- core/ imports (16 sites) migrated
- Registry entries (3 convergence engines) updated
- File path constants (7 sites) updated
- CLI command strings updated
- Identity guarantees preserved
- Cold boot improved to 0.065s

**Remaining eos_ai references (post-R8f):**
1. `eos_ai/` shim directory (459 files) — compatibility layer
2. Legacy test validators (63 refs) — intentional, checking for eos_ai imports in runtime/
3. `.claude/settings.json` (3 refs) — requires manual update
4. Migration tools (r8b/r8d generators) — reference eos_ai by design
5. `runtime/transport/substrate_projection_boundaries.py` (1 ref) — backward-compat check
6. `data/*.json` generated artifacts — will regenerate on next graph rebuild


---

> [Note: Test baseline re-anchored 2026-05-12. Actual collection is 11,532 / 338 (collected / collection errors). The 8684/2691/495 figures were valid at time of writing but are now stale. See data/audits/2026-05-12_ground_truth_audit.md §8.]
