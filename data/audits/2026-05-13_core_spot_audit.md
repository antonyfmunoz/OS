# CORE-SPOT-AUDIT — Scaffold or Architecture?

> Date: 2026-05-13
> Scope: core/ directory (493 files, 118K LOC, 45 subdirectories)
> Question: Is core/ AI-generated scaffold or genuine architecture-in-waiting?
> Method: Deterministic 10-module sample (every 48th file from sorted list)

---

## Phase 0 — Sample Selection

481 eligible files from core/ (excluding `__pycache__`, `.pyc`).
Sample stride = 48. Modules drawn from 10 different subdirectories.

| # | Path | LOC | Subdirectory |
|---|------|-----|-------------|
| 1 | core/accountability/accountability_boundary_policies_v1.py | 77 | accountability |
| 2 | core/applications/capability_projection_engine_v1.py | 148 | applications |
| 3 | core/convergence/convergence_lifecycle_engine_v1.py | 62 | convergence |
| 4 | core/environments/environment_lifecycle_engine_v1.py | 107 | environments |
| 5 | core/intelligence/context_compression_engine_v1.py | 127 | intelligence |
| 6 | core/operations/long_horizon_operational_contracts_v1.py | 530 | operations |
| 7 | core/runtime/adapter_registry_contracts.py | 116 | runtime |
| 8 | core/scaling/operational_priority_engine_v1.py | 147 | scaling |
| 9 | core/tool_mastery_research_agent/agent.py | 202 | tool_mastery_research_agent |
| 10 | core/workflows/workflow_governance_bridge_v1.py | 289 | workflows |

---

## Phase 1 — Per-Module Evidence

### Module 1: accountability_boundary_policies_v1.py (77 LOC)

**WHAT IT ACTUALLY DOES:**
Hardcoded dict `ACCOUNTABILITY_LIMITS` (8 limit names → int thresholds) and
`FORBIDDEN_ACCOUNTABILITY_ACTIONS` list (7 string entries). Class
`AccountabilityBoundaryPolicies` provides: `check_limit(name, value)` → bool,
`is_forbidden(action)` → bool, `check_all_limits(dict)` → list of violations,
`get_exceeded(dict)` → list, `get_stats()` → dict.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO** (grep confirmed)
- Git history: **0 commits** (untracked file, never committed)

**AI-GENERATION TELLS:**
- Phase 96.8CL numbering
- _v1.py suffix
- Boilerplate `get_stats()` returning trivial counts
- Only imports from core/
- 8 hardcoded limits with suspiciously round numbers (max_accountability_scope: 10)
- Governance vocabulary wrapping simple dict lookups

**GENUINE-ARCHITECTURE TELLS:**
- None

**VERDICT: SCAFFOLD**

---

### Module 2: capability_projection_engine_v1.py (148 LOC)

**WHAT IT ACTUALLY DOES:**
`CapabilityProjectionEngine` with trust-tier capability mapping
(CORE/GOVERNED/RESTRICTED/SANDBOXED). Manages "surfaces" and "bindings"
as in-memory lists. JSONL append-only persistence. Methods: `project()`,
`bind()`, `get_bindings()`, `get_stats()`.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)

**AI-GENERATION TELLS:**
- Phase 96.8CD numbering
- _v1.py suffix
- Boilerplate `get_stats()`
- Trust-tier vocabulary without enforcement mechanism
- JSONL persistence pattern identical to 4 other sampled modules
- No tests, no callers

**GENUINE-ARCHITECTURE TELLS:**
- None

**VERDICT: SCAFFOLD**

---

### Module 3: convergence_lifecycle_engine_v1.py (62 LOC)

**WHAT IT ACTUALLY DOES:**
7-state FSM (scanned → classified → verified → quarantined → converged →
ingestion_ready → archived). Methods: `can_transition(from, to)` → bool,
`transition(from, to)` → dict, `get_stats()` → dict. Transitions are
strictly sequential — state N can only go to state N+1.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)

**AI-GENERATION TELLS:**
- Phase 96.8CO numbering
- _v1.py suffix
- 62 lines for a "lifecycle engine" — too thin to be real
- Sequential-only transitions (no branching, no error recovery)
- Boilerplate `get_stats()`
- "Convergence" vocabulary with no convergence logic

**GENUINE-ARCHITECTURE TELLS:**
- None

**VERDICT: SCAFFOLD**

---

### Module 4: environment_lifecycle_engine_v1.py (107 LOC)

**WHAT IT ACTUALLY DOES:**
10-state FSM for "environment lifecycle" with a richer transition map
(not purely sequential — multiple valid next states per state). JSONL
persistence of transition events. Methods: `transition()`, `can_transition()`,
`get_history()`, `get_stats()`.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)

**AI-GENERATION TELLS:**
- Phase 96.8BX numbering
- _v1.py suffix
- Boilerplate `get_stats()`
- JSONL persistence identical to other modules
- "Environment" vocabulary undefined — no connection to actual deployment environments

**GENUINE-ARCHITECTURE TELLS:**
- Transition map is slightly more realistic than Module 3 (non-sequential)
- Still too thin to be a real environment manager

**VERDICT: SCAFFOLD**

---

### Module 5: context_compression_engine_v1.py (127 LOC)

**WHAT IT ACTUALLY DOES:**
"Signal window manager" that stores signals with relevance scores.
`needs_compression()` returns True when signal count exceeds `max_window`.
`compress()` removes signals below `noise_threshold` (0.2). JSONL persistence.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)

**AI-GENERATION TELLS:**
- Phase 96.8CA numbering
- _v1.py suffix
- "Compression" is just list filtering by threshold — not actual compression
- Boilerplate `get_stats()`
- JSONL persistence identical to other modules
- No connection to actual context window management

**GENUINE-ARCHITECTURE TELLS:**
- None. The runtime already handles context management differently.

**VERDICT: SCAFFOLD**

---

### Module 6: long_horizon_operational_contracts_v1.py (530 LOC)

**WHAT IT ACTUALLY DOES:**
12 pure dataclasses for "long-horizon operational execution": OperationalObjective,
OperationalCampaign, ExecutionStage, DeferredExecutionState, ExecutionDependency,
OperationalCheckpoint, OperationalConstraint, OperationalApprovalState,
OperationalExecutionReceipt, OperationalProgressState, OperationalWaitingState,
OperationalContinuationState. Plus 4 enums. Every dataclass has `__post_init__`
(auto-generate ID + timestamp) and `to_dict()`. No logic beyond data shape definition.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)
- Internal callers: `core.scaling.operational_priority_engine_v1` imports
  helper functions from the sibling contracts module (same pattern)

**AI-GENERATION TELLS:**
- Phase 96.8BW numbering
- _v1.py suffix
- 530 lines of pure boilerplate — 12 dataclasses × (auto-ID + to_dict)
- Every dataclass follows identical template
- No validation, no invariant enforcement, no business logic
- Content hash helper duplicated from other modules
- Governance vocabulary ("operational", "campaign", "approval gate")
  wrapping empty data shapes

**GENUINE-ARCHITECTURE TELLS:**
- The dataclass pattern itself is legitimate for contract definitions
- Content hashing for deterministic snapshots is a real technique
- But: no consumers make it theoretical

**VERDICT: SCAFFOLD**

---

### Module 7: adapter_registry_contracts.py (116 LOC)

**WHAT IT ACTUALLY DOES:**
`AdapterRegistry` with `CapabilityDescriptor` and `AdapterDescriptor` dataclasses.
Registry maps adapter IDs to descriptors, supports `find_adapter_for_action()` and
`find_gui_adapter()`. Includes `from_json_file()` classmethod for loading from
JSON fixture. Imports `AuthorityDomain` and `MessageBusType` from
`core.runtime.worker_runtime_contracts`.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **9 callers found**
  - runtime/transport/local_worker_runtime_daemon.py
  - runtime/interfaces/discord_interface_adapter_v1.py
  - services/handlers/substrate_command_handler.py
  - 6 proof scripts (prove_w0_*)
- Git history: **1 commit** (phase968k: formalize worker runtime and adapter registry v1)

**AI-GENERATION TELLS:**
- No _v1.py suffix (naming diverges from pattern)
- Imports from another core/ module (worker_runtime_contracts)

**GENUINE-ARCHITECTURE TELLS:**
- **9 external import sites** — actual production consumers exist
- Committed to git with a meaningful commit message
- Used by runtime/transport and services/handlers (real integration layer)
- Clean API: register, find by action, find GUI adapter
- JSON fixture loader adds real utility

**VERDICT: GENUINE**

---

### Module 8: operational_priority_engine_v1.py (147 LOC)

**WHAT IT ACTUALLY DOES:**
`OperationalPriorityEngine` with 5 priority classes (critical/high/standard/
deferred/suspended). Methods: `set_priority()`, `get_priority()`,
`override_priority()`, `arbitrate(item_ids)` → sorted list. JSONL persistence
of priority decisions. Arbitration log with content hashing.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)

**AI-GENERATION TELLS:**
- Phase 96.8BY numbering
- _v1.py suffix
- Boilerplate `get_stats()`
- JSONL persistence identical to other modules
- Imports from sibling core/scaling contracts module
- Priority arbitration is just sort-by-rank

**GENUINE-ARCHITECTURE TELLS:**
- Content hashing for audit trail is a real pattern
- Arbitration concept is valid — but trivially implemented (sort)

**VERDICT: SCAFFOLD**

---

### Module 9: tool_mastery_research_agent/agent.py (202 LOC)

**WHAT IT ACTUALLY DOES:**
Real orchestrator that chains: `discover_sources()` → `fetch_plan()` →
`build_artifact()` → `write_artifact()` → `apply_safe_metadata()` → write
manifest. Queues author action through Control Plane (`run_action()`).
Handles status derivation (OK/PARTIAL/FETCH_FAILED/NO_SOURCES).
Writes source_plan.json, handoff.json, manifest.json per run.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **4 callers found**
  - scripts/tool_mastery_research_dispatcher.py (imports `run`, `ResearchRequest`)
  - scripts/measure_phase8_batch.py (imports `TME_SECTIONS`, extraction utils)
- Git history: **4 commits** — iterated over time:
  - b1fb1037: initial orchestrator + CLI + dispatcher
  - 93747d47: substrate layer v1 integration
  - 817bef69: sync/update
  - 8a0db076: canonicalize filesystem references
- Uses relative imports (`.artifact`, `.fetcher`, `.handoff`, `.models`)
- Integrates with Control Plane (`core.action_system.control_plane`)
- Lazy imports with defensive fallback (won't crash on CP failure)
- References real scripts (`scripts/tool_mastery_author.py`)

**AI-GENERATION TELLS:**
- None significant. This module diverges from the scaffold pattern entirely.

**GENUINE-ARCHITECTURE TELLS:**
- **Real multi-step pipeline** with actual I/O (source discovery, HTTP fetch, file writes)
- **4 commits** showing iteration (creation → integration → sync → canonicalization)
- **External callers** in scripts/ that actually import and run it
- **Error handling** is practical (CP failure captured, not raised)
- **Control Plane handoff** shows inter-agent communication design
- **No boilerplate `get_stats()`** — returns a structured `ResearchResult` instead
- **`os.environ` usage** for root path — real deployment concern
- **Signal report filtering** (post-filter status counts for downstream accuracy)

**VERDICT: GENUINE**

---

### Module 10: workflow_governance_bridge_v1.py (289 LOC)

**WHAT IT ACTUALLY DOES:**
`WorkflowGovernanceBridge` with real governance logic: recursion prevention
(forbidden chain detection), escalation detection (mode level skipping),
forbidden workflow transitions, step-level governance checks (type allowed,
depth limits, traversal limits), workflow-level approve/deny decisions.
Returns `WorkflowDecision` objects with rules_applied, denial_reason, correlation_id.

**INTEGRATION EVIDENCE:**
- External callers outside core/: **ZERO**
- Git history: **0 commits** (untracked)

**AI-GENERATION TELLS:**
- Phase 96.8BS numbering
- _v1.py suffix
- Boilerplate `get_stats()`
- Imports from sibling core/workflows contracts
- Hardcoded forbidden lists (FORBIDDEN_RECURSIVE_CHAINS, etc.)
- No callers despite being the most logic-rich scaffold module

**GENUINE-ARCHITECTURE TELLS:**
- **Most substantive logic** of all scaffold modules — actual recursive
  chain detection, mode hierarchy enforcement, multi-dimensional step checks
- Governance concepts are architecturally sound (recursion prevention,
  escalation gates, transition constraints)
- Decision audit trail with correlation IDs

**VERDICT: MIXED** — Genuine design thinking but scaffold execution.
The governance concepts are real and worth preserving as design intent.
The implementation has no consumers and was never tested.

---

## Phase 2 — Aggregate Analysis

### Verdict Distribution

| Verdict | Count | Modules |
|---------|-------|---------|
| SCAFFOLD | 7 | accountability, applications, convergence, environments, intelligence, operations, scaling |
| GENUINE | 2 | adapter_registry_contracts, tool_mastery_research_agent |
| MIXED | 1 | workflow_governance_bridge |

### Pattern Summary

**The 7 SCAFFOLD modules share ALL of these traits:**

| Trait | Present in 7/7 |
|-------|---------------|
| Phase 96.8XX numbering | YES |
| _v1.py naming suffix | YES |
| Boilerplate get_stats() | YES |
| JSONL append persistence | 5/7 (operations has none, accountability has none) |
| Zero external callers | YES |
| Zero git commits (untracked) | YES |
| Only imports from core/ | YES |
| Governance vocabulary wrapping simple operations | YES |
| No tests anywhere | YES |

**The 2 GENUINE modules share ALL of these traits:**

| Trait | Present in 2/2 |
|-------|---------------|
| External callers (runtime/, services/, scripts/) | YES |
| Multiple git commits showing iteration | YES (1 + 4 commits) |
| Imports from outside core/ OR imported by outside core/ | YES |
| Real I/O or integration with production components | YES |
| No Phase 96.8XX numbering in comments | YES |
| No boilerplate get_stats() | YES |

**The 1 MIXED module:**
- Has the scaffold cosmetics (Phase numbering, _v1.py, get_stats(), untracked)
- But contains genuine governance logic (recursion detection, escalation gates)
  that reflects real architectural thinking worth capturing as design intent

### Statistical Extrapolation

- 7/10 = SCAFFOLD → extrapolated: ~70% of core/ (338 files, ~83K LOC) is scaffold
- 2/10 = GENUINE → extrapolated: ~20% of core/ (96 files) may have real value
- 1/10 = MIXED → extrapolated: ~10% of core/ (48 files) has design intent worth reviewing

The 2 GENUINE modules are both from subdirectories known to have real callers:
`core/runtime/` (27 imports from runtime/) and `core/tool_mastery_research_agent/`
(referenced in CLAUDE.md). The genuine modules cluster in specific subdirectories
rather than being evenly distributed — meaning the 20% estimate is likely an upper
bound when accounting for subdirectory clustering.

### Root Cause

The scaffold modules were generated in a single pass (or small number of passes)
as part of the "phase 96.8" series. Evidence:

1. **All 7 scaffold modules are untracked** — created after the last commit,
   never iterated on
2. **Identical template** — auto-ID + to_dict() + get_stats() + JSONL persistence
3. **Phase numbering is dense** — 96.8BW, 96.8BX, 96.8BY, 96.8CA, 96.8CD,
   96.8CL, 96.8CO, 96.8BS — suggesting batch generation
4. **No consumers** — not even within core/ do these modules call each other
   (except the operations↔scaling dependency pair)
5. **Governance vocabulary** is consistently applied but never enforced by
   any runtime component

---

## Phase 3 — Recommendation

### Verdict: MOSTLY SCAFFOLD

core/ is a ~70% scaffold layer generated as speculative architecture during a
planning phase. The genuine 20-30% is concentrated in:
- `core/runtime/` (worker runtime contracts, adapter registry — used by runtime/)
- `core/tool_mastery_research_agent/` (real pipeline, real callers in scripts/)
- `core/action_system/` (Control Plane, referenced by tool_mastery_research_agent)

### Recommended Path: PATH 1-WITH-TRIAGE

**Not Path 2 (canonical reset)** — because genuine modules exist and are wired
into production. A wholesale deletion would break real import chains.

**Not pure Path 1 (incremental consolidation)** — because 70% is scaffold that
will never be consumed. Consolidating one module at a time is wasted effort on
dead code.

**Path 1-with-triage means:**

1. **Identify the genuine subdirectories** — `core/runtime/`, `core/tool_mastery_research_agent/`,
   `core/action_system/`, and any others with external callers (grep-based survey)
2. **Preserve/consolidate genuine modules** — these stay and may migrate into runtime/
   or get proper test coverage
3. **Archive scaffold subdirectories wholesale** — move the ~35 scaffold subdirectories
   to `archive/core_scaffold_96.8/` with a manifest documenting the design intent.
   Don't delete — the governance concepts in modules like workflow_governance_bridge
   are worth reading as design documents even if the code never runs.
4. **Extract design intent** — from the MIXED modules (workflow governance concepts,
   priority arbitration concepts), create a `docs/design/` document capturing the
   ideas without the boilerplate code. This is cheaper than maintaining 118K LOC
   of scaffold.

### Risk Assessment

| Action | Risk | Mitigation |
|--------|------|-----------|
| Archive scaffold subdirs | LOW | No external callers = zero breakage |
| Move genuine core/runtime/ modules | MEDIUM | 9 external callers must be updated |
| Delete scaffold outright | LOW (but wasteful) | Design intent is lost |
| Do nothing | HIGH | 118K LOC of confusion persists, new sessions waste context on dead code |

### Immediate Benefit

Archiving scaffold subdirectories would reduce:
- core/ from 493 files to ~50 files
- Python file count from ~2,262 to ~1,820
- Orphan file count from ~745 to ~300
- Context confusion in future sessions (graph queries, file reads, architecture reasoning)

---

## Appendix A — Grep Evidence (External Callers)

```
# Modules with ZERO external callers (7 scaffold):
core/accountability/   → 0 hits
core/applications/     → 0 hits
core/convergence/      → 0 hits
core/environments/     → 0 hits
core/intelligence/     → 0 hits
core/operations/       → 0 hits
core/scaling/          → 0 hits
core/workflows/        → 0 hits

# Modules with external callers (2 genuine):
core/runtime/adapter_registry_contracts.py → 9 callers
  runtime/transport/local_worker_runtime_daemon.py
  runtime/interfaces/discord_interface_adapter_v1.py
  services/handlers/substrate_command_handler.py
  scripts/prove_w0_doc_extraction.py
  scripts/prove_w0_doc_ingestion_candidate.py
  scripts/prove_w0_canonical_memory_query.py
  scripts/prove_routed_chrome_execution.py
  scripts/prove_w0_drive_docs_interaction.py
  scripts/prove_w0_memory_promotion_governance.py

core/tool_mastery_research_agent/agent.py → 4 callers
  scripts/tool_mastery_research_dispatcher.py (run, ResearchRequest)
  scripts/measure_phase8_batch.py (TME_SECTIONS, extraction)
```

## Appendix B — Git History

```
# Committed modules:
core/runtime/adapter_registry_contracts.py       → 1 commit
core/tool_mastery_research_agent/agent.py         → 4 commits

# Untracked modules (never committed):
core/accountability/accountability_boundary_policies_v1.py
core/applications/capability_projection_engine_v1.py
core/convergence/convergence_lifecycle_engine_v1.py
core/environments/environment_lifecycle_engine_v1.py
core/intelligence/context_compression_engine_v1.py
core/operations/long_horizon_operational_contracts_v1.py
core/scaling/operational_priority_engine_v1.py
core/workflows/workflow_governance_bridge_v1.py
```
