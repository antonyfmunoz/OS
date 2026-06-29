# C31 Phase 5 Report — Execution Pipeline Hardening

**Date:** 2026-06-29
**Branch:** worktree-c31-phase5
**Scope:** Wire the learning loop to the governed spine, connect capability compounding, expand observability.

---

## 1. Audit Findings

| Area | Status Before Phase 5 |
|------|----------------------|
| GovernedExecutionSpine | **WIRED** — 5 callers (gateway, plan adapter, workload, assisted, maintenance) |
| Learning loop | **INDIRECT** — only via propagation engine handler chain |
| Capability compounding | **UNWIRED** — not in daemon, not observable |
| LearningSignal type | **DUAL** — protocols.py (agent-level) + outcome_learning.py (execution-level) |
| Mutation bypasses | **LOW** — 9 in substrate/, all legitimate adapter code |
| Cockpit observability | **COMPREHENSIVE** — 20+ endpoints already existed |

---

## 2. Changes Made

### 2a. Spine → Learning Loop (Direct Path)

**File:** `substrate/organism/governed_spine.py`

- Added `learning_loop: OutcomeLearningLoop | None` parameter to `__init__`
- Added `_record_learning()` method — converts ActionEnvelope outcome to OutcomeRecord and feeds it directly to the learning loop
- Called after every execution (success, failure, or exception)
- Maps envelope status to OutcomeStatus: SUCCESS → success, VERIFICATION_FAILED → partial, FAILED → failure
- Non-fatal — if learning loop raises, it's caught and logged at debug level
- `to_dict()` now includes `learning_loop_connected` boolean and `learning_summary` stats

**Why direct instead of relying on propagation only:**
The propagation engine path works but is fragile — if propagation_engine is None, no learning happens. The direct path ensures every spine execution records an outcome regardless of propagation state.

### 2b. Capability Compounding in Daemon

**File:** `substrate/organism/daemon.py`

- Added `CapabilityCompoundingRuntime` import and initialization
- Added `capability_compounding` property
- Added `capability_compounding` snapshot to daemon's `to_dict()` output

### 2c. Enhanced Observability

**File:** `transports/api/cockpit_spine_router.py`

- Added `/organism/capability-compounding` endpoint (read-only) — returns compounding pipeline snapshot
- Enhanced `/organism/reliability` endpoint — now includes `learning_loop_connected` and `learning` stats (total outcomes, signals, reliability scores)
- Total cockpit spine endpoints: **22** (was 20)

### 2d. New Tests

**File:** `tests/test_c31_spine_learning.py` (7 tests)

- `test_successful_execution_records_learning` — verifies success flows to learning loop
- `test_failed_execution_records_learning` — verifies failure flows to learning loop
- `test_exception_execution_records_learning` — verifies exception flows to learning loop
- `test_multiple_executions_track_reliability` — verifies reliability scoring accumulates
- `test_spine_without_learning_loop_works` — verifies backward compatibility (learning_loop=None)
- `test_to_dict_includes_learning_stats` — verifies stats appear in to_dict
- `test_to_dict_without_learning` — verifies clean output when no learning loop

---

## 3. LearningSignal Type Decision

Two `LearningSignal` classes exist — they serve genuinely different purposes:

| Version | Location | Purpose | Used by |
|---------|----------|---------|---------|
| Pydantic BaseModel | `protocols.py:68` | Agent-level pattern learning (agent_id, deliverable_id, confidence) | agent_runtime.py, store.py |
| dataclass | `outcome_learning.py:81` | Execution outcome tracking (signal_type, action_type, old_value, new_value) | Internal to OutcomeLearningLoop |

**Decision:** No rename needed. The outcome_learning version is module-internal (no external imports). The protocols.py version is the canonical agent-level type. Different concepts, same name is acceptable because scope is non-overlapping.

---

## 4. Mutation Bypass Assessment

Only 9 direct file/subprocess calls in substrate/ outside the spine (excluding cpu_gate, tests, _dormant):

| File | Operation | Verdict |
|------|-----------|---------|
| `person_recognition.py` | file write | Legitimate — research data persistence |
| `shell_runtime_adapter.py` | subprocess.Popen | Legitimate — IS the subprocess adapter |
| `worktree_sandbox.py` | shutil.rmtree | Legitimate — sandbox cleanup |
| `ideal_week.py` | file write | Legitimate — schedule state |

**Decision:** These are all infrastructure-level operations that ARE adapters or state persistence. Routing them through the spine would add ceremony without governance value. The spine is for organism-level mutations (deployments, container ops, git ops, etc.), not low-level adapter internals.

---

## 5. Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_c31_spine_learning.py` | **7/7 passed** |
| `pytest tests/substrate/` | **70/70 passed** |
| `pytest tests/adapters/` | **50/50 passed** |
| `pytest tests/test_spine_full.py` | **9/9 passed** |
| `check_dependency_direction.py --all` | **1262 files clean** (70 legacy) |
| `py_compile` all modified files | **All pass** |
| `ruff format` all modified files | **Clean** |

---

## 6. Execution Pipeline State (Post Phase 5)

```
Intent → ActionEnvelope
  → GovernedExecutionSpine.submit()
    → governance_check (mode + mutation registry)
    → approval_gate (auto or operator)
    → execute (with retry)
    → verify (optional)
    → rollback (on failure, optional)
    → record_learning ← NEW (direct path)
    → journal record
    → event emit
    → coherence propagation (learning, templates, memory, capability)
    → leverage metrics
```

**Learning loop:**
- **Direct path:** spine → OutcomeLearningLoop.record_outcome() (always fires)
- **Propagation path:** spine → ParallelPropagationEngine → outcome_learning_handler (fires when engine wired)
- Both paths are additive — the direct path ensures learning happens even if propagation is disabled

**Capability compounding:**
- Read-only composition across 5 subsystems
- Now initialized in daemon, observable via cockpit
- Pipeline: Outcome → Lesson → Pattern → Capability → Operational Asset

---

## 7. Campaign Status

| Phase | Status |
|-------|--------|
| Phase 1: Ground Truth Audit | **COMPLETE** |
| Phase 2: Substrate Stabilization | **COMPLETE** (steps 5, 7 deferred) |
| Phase 3: Protocol Consolidation | **COMPLETE** |
| Phase 4: Adapter Internalization | **COMPLETE** |
| Phase 5: Execution Pipeline Hardening | **COMPLETE** |
| Phase 6: Daily Driver Operationalization | Next |
| Phase 7: Verification & Campaign Closure | Pending |

**Net impact this phase: +4 files modified, +1 test file added, 22 cockpit endpoints (was 20), learning loop directly wired to spine.**
