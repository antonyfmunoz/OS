# Layering Violations Report — Phase 75A

> Generated: 2026-05-02 | Violations found: 33 (10 boundary + 23 cycles)

---

## PRD Invariant Checks

### 1. Control Plane Exclusivity

**Rule**: All external interaction routes through the control plane.

**Status**: MOSTLY COMPLIANT

**Compliant paths**:
- `umh.control.api` → `umh.execution.engine.execute()` — correct
- `umh.control.cli` → same engine path — correct
- `umh.gateway.entry.translate_and_run()` → `umh.run.run()` — correct

**Violations**:
- `umh.interfaces.discord.bot` has direct execution paths that bypass `umh.control.api`
  (59 imports, highest fan-out). The Discord bot calls substrate modules directly.
- `umh.interfaces.telegram.bot` similarly bypasses (33 imports).
- `umh.runtime_engine.session_runtime` (38 imports) orchestrates execution
  without routing through the control plane.

**Assessment**: EXPECTED for current phase. Interfaces were built before the control plane
existed. They should be migrated to route through `umh.gateway.entry` but this is a
Phase 75B+ concern.

**Remediation**: In 75B, interfaces should call `translate_and_run()` or `POST /run`
instead of direct substrate calls.

### 2. Adapter Isolation

**Rule**: Adapters are pure executors. No business logic. No decisions.

**Status**: COMPLIANT (adapters package)

**Confirmed**: All 30 adapter modules follow the protocol pattern. Adapters implement
`Adapter` protocol from `umh.adapters.contracts`. No decision logic found in adapter layer.

**Edge case**: `umh.adapters.model_router` contains routing logic (which model to use).
This is capability routing, not business logic. Acceptable.

### 3. Typed Contracts Only

**Rule**: All subsystem-to-subsystem interaction uses typed contracts from `umh.protocols`.

**Status**: PARTIAL COMPLIANCE

**Compliant**: Execution (ExecutionRequest/Result), Governance (AuthorityLevel),
Signal (SignalBundle), Intent (IntentType), Feedback (OutcomeType), Adapters (Adapter protocol).

**Violations**:
- `umh.runtime` modules pass raw dicts between components (scores, weights, regime state)
  instead of typed dataclasses. This is the intelligence kernel — it was built for speed.
- `umh.substrate` modules use ad-hoc dict structures for operator state.

**Assessment**: LOW risk for MVP. Intelligence kernel has internal consistency through
convention. Typing should be added incrementally.

### 4. Single Execution Spine

**Rule**: All execution flows through `umh.execution.engine.execute()`.

**Status**: VIOLATED — multiple execution paths exist

**Canonical path**: `umh.execution.engine.execute()` — correct single entry point.

**Bypass paths**:
1. `umh.runtime_engine.execution_spine` — legacy parallel execution spine
2. `umh.runtime_engine.execution_engine` — legacy execution engine
3. `umh.substrate.execution_worker` — substrate direct execution
4. `umh.substrate.execution_adapter` — substrate adapter execution
5. `umh.substrate.run_execution` — substrate run execution
6. `umh.runtime_loop.action_executor` — runtime loop direct execution

**Assessment**: MEDIUM risk. The execution.engine is the correct canonical path but
substrate and runtime_loop have their own execution paths for live operational needs.
Phase 75B must consolidate these to route through the single spine.

### 5. Memory Discipline

**Rule**: All state writes go through the memory subsystem.

**Status**: MOSTLY COMPLIANT

**Compliant**: `umh.memory.storage`, `umh.memory.persistent_store`, `umh.feedback.loop`
all use the StorageBackend abstraction.

**Violations**:
- `umh.runtime_engine.persistence` writes directly to filesystem (JSON files)
  instead of through storage backend.
- `umh.prediction.persistence.FilePredictionBackend` writes to filesystem directly.
- `umh.substrate.storage` has its own persistence path.

**Assessment**: LOW risk for MVP. Filesystem persistence is legitimate for local state
that doesn't need cross-instance sharing. Neon is the canonical persistent store.

### 6. Governance First

**Rule**: No execution without governance check.

**Status**: COMPLIANT in run loop, VIOLATED in substrate

**Compliant**: `umh.run.run()` calls `check_governance()` before execution (stage 7).

**Violations**:
- `umh.substrate.execution_worker` can execute without governance gate
- `umh.runtime_loop.action_executor` executes actions without governance check
- `umh.runtime_engine.execution_spine` has its own authority check (not `umh.governance`)

**Assessment**: MEDIUM risk. Live operational paths (substrate, runtime_loop) bypass
the governance layer. Phase 75B must wire governance into all execution paths.

### 7. Environment Explicitness

**Rule**: All execution knows what environment it's running in.

**Status**: COMPLIANT

`umh.environments.system_context` (51 fan-in) is the third most imported module.
Nearly all execution-adjacent code checks the system context before acting.

---

## Reality-Kernel Invariant Checks

### No scoring module directly executes

**Status**: COMPLIANT
No `scoring` or `score` modules import from `execution` or `execute` modules.
Scanner found 0 scoring→execution violations.

### No pattern/learning module mutates historical records

**Status**: COMPLIANT
Scanner found 0 pattern→memory.store violations.
Pattern modules read from stores but do not write to historical records.

### Optional influence remains default-off

**Status**: COMPLIANT (by design)
Intelligence kernel modules use bounded influence factors (0.80–1.20 range).
Default values are neutral (1.0 or 0.5). No module forces influence without config.

### No environment/subprocess/docker imports outside allowed layers

**Status**: 10 VIOLATIONS

| Module | Import | Layer |
|--------|--------|-------|
| `umh.interfaces.discord.bot` | subprocess (2x) | interface |
| `umh.interfaces.telegram.bot` | subprocess | interface |
| `umh.runtime_engine.cc_sdk` | subprocess | runtime_engine |
| `umh.runtime_engine.email_gps` | subprocess | runtime_engine |
| `umh.runtime_engine.gws_connector` | subprocess | runtime_engine |
| `umh.runtime_engine.notebooklm_sync` | subprocess | runtime_engine |
| `umh.runtime_engine.orchestrator` | subprocess | runtime_engine |
| `umh.runtime_engine.system_health` | subprocess | runtime_engine |
| `umh.runtime_engine.voice_engine` | subprocess | runtime_engine |

**Assessment**: All are in legacy layers (runtime_engine, interfaces).
None are in the clean UMH packages. Not blocking for MVP.

---

## Package-Level Cycles (23)

### Critical Cycles (require remediation for clean architecture)

1. **execution ↔ adapters** — bidirectional coupling
   - Fix: execution depends on protocols, adapters implement protocols
   
2. **adapters ↔ runtime_loop ↔ protocols** — circular through lifecycle
   - Fix: runtime_loop depends on protocols only, not adapters directly

3. **goals ↔ strategy ↔ planning** (through protocols)
   - Fix: goals defines state, strategy reads it, planning consumes both — break via protocols

### Tolerable Cycles (legacy cross-cutting)

4. **runtime_engine ↔ planning ↔ persistence_layer ↔ substrate**
   - Legacy wiring. Will resolve as runtime_engine modules are deprecated.

5. **substrate ↔ world ↔ memory ↔ orchestrator ↔ execution ↔ adapters**
   - Long chain through operator layer. Expected for a live operational surface.

---

## Summary

| Check | Status | Violations | MVP Risk |
|-------|--------|-----------|----------|
| Control Plane Exclusivity | PARTIAL | 3 bypass paths | LOW |
| Adapter Isolation | COMPLIANT | 0 | NONE |
| Typed Contracts Only | PARTIAL | Runtime kernel uses dicts | LOW |
| Single Execution Spine | VIOLATED | 5 parallel paths | MEDIUM |
| Memory Discipline | MOSTLY | 3 filesystem paths | LOW |
| Governance First | PARTIAL | 3 ungoverned paths | MEDIUM |
| Environment Explicitness | COMPLIANT | 0 | NONE |
| No scoring→execute | COMPLIANT | 0 | NONE |
| No pattern→mutate | COMPLIANT | 0 | NONE |
| Optional influence off | COMPLIANT | 0 | NONE |
| No env imports outside layers | VIOLATED | 10 legacy modules | LOW |
| Package cycles | VIOLATED | 23 cycles | LOW |

**Overall**: Architecture is sound in the clean packages. Violations are concentrated
in legacy layers (runtime_engine, substrate, interfaces) that predate the clean
architecture. Phase 75B should focus on wiring governance and execution consolidation.
