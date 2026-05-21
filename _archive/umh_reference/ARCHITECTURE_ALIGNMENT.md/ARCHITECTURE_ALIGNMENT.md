# Phase 5B: UMH Target Architecture Alignment

## Invariant

No signal, decision, action, tool call, device operation, workflow,
memory write, or learning update may bypass the UMH control plane.

---

## 1. Current-to-Target Mapping Table

| Current Path | Current Responsibility | Target Subsystem | Notes |
|---|---|---|---|
| `__init__.py` | Public API surface | `core/` | Becomes `core/__init__.py` re-exporting `run()` |
| `__main__.py` | CLI interface | `interface/` | CLI is an interface adapter |
| `run.py` | 9-stage orchestration loop | `core/` | The control plane spine |
| **adapters/** | | | |
| `adapters/__init__.py` | Docstring | `adapters/` | Keep |
| `adapters/base.py` | Adapter protocols + null stubs + registry | `adapters/` | Keep, rename to `protocols.py` |
| `adapters/llm.py` | Ollama + HTTP LLM implementations | `adapters/` | Keep |
| **capability/** | | | |
| `capability/__init__.py` | Docstring | `capabilities/` | Rename package |
| `capability/registry.py` | CapabilityRegistry, PerformanceStats, Capability | `capabilities/` | Rename package |
| `capability/router.py` | RoutingDecision, route_to_capability | `capabilities/` | Rename package |
| **context/** | | | |
| `context/__init__.py` | Re-exports | `composition/` | Context assembly IS composition |
| `context/budget.py` | TokenBudget | `composition/` | |
| `context/builder.py` | ContextBuilder | `composition/` | |
| `context/types.py` | ContextPriority, ContextSection, ContextResult | `composition/` | |
| **decision/** | | | |
| `decision/__init__.py` | Docstring | `observability/` | DecisionTrace is pure observability |
| `decision/trace.py` | DecisionTrace (1066 lines, 200+ fields) | `observability/` | Massive observability type |
| **execution/** | | | |
| `execution/__init__.py` | Docstring | `execution/` | Keep |
| `execution/contract.py` | ExecutionRequest, ExecutionResult, etc. | `protocols/` | These are protocol contracts |
| `execution/engine.py` | execute() single entry point | `execution/` | Keep |
| `execution/harness.py` | AgentHarness, multi-step orchestration | `execution/` | Keep |
| `execution/interfaces.py` | ExecutionBackend, ExecutionObserver protocols | `protocols/` | Protocol contracts |
| `execution/pipeline.py` | ExecutionPipeline, composable stages | `execution/` | Keep |
| `execution/quality.py` | QualityGate, 4-lens transformation | `execution/` | Or `governance/` (quality enforcement) |
| `execution/stages.py` | StageContext, ExecutionStage protocol | `execution/` | Keep |
| **feedback/** | | | |
| `feedback/__init__.py` | Docstring | `learning/` | Rename package |
| `feedback/dynamics.py` | FeedbackDynamics, delayed/compounding scores | `learning/` | |
| `feedback/loop.py` | record_outcome, FeedbackEvent | `learning/` | |
| **goals/** | | | |
| `goals/__init__.py` | Docstring | `planning/` | Goals drive planning |
| `goals/engine.py` | GoalEngineState, weight adaptation | `planning/` | |
| `goals/interfaces.py` | GoalPersistence protocol | `protocols/` | Protocol contract |
| `goals/objective.py` | ObjectiveFunction, ObjectiveSet | `planning/` | |
| `goals/state.py` | GoalState, GoalRegistry, GoalTracker | `planning/` | |
| **governance/** | | | |
| `governance/__init__.py` | Docstring | `governance/` | Keep |
| `governance/authority.py` | AuthorityLevel, GovernanceDecision | `governance/` | Keep |
| `governance/capability.py` | CapabilityEnforcer, ProfileRegistry | `governance/` | Keep |
| `governance/governor.py` | ImprovementProposal, Governor | `governance/` | Keep |
| **intent/** | | | |
| `intent/__init__.py` | Docstring | `interpretation/` | Rename package |
| `intent/compiler.py` | compile_intent, Intent | `interpretation/` | |
| **memory/** | | | |
| `memory/__init__.py` | Docstring | `storage/` | Rename package |
| `memory/storage.py` | StorageBackend, InMemoryStorage | `storage/` | |
| **primitives/** | | | |
| `primitives/__init__.py` | Docstring | `ontology/` | Rename package |
| `primitives/ontological.py` | PrimitiveTag, L0, validation | `ontology/` | |
| **signal/** | | | |
| `signal/__init__.py` | Docstring | `interpretation/` | Merge with intent → interpretation |
| `signal/event_bus.py` | EventBus, EventRegistry | `core/` | Event bus is core infrastructure |
| `signal/ingest.py` | classify_input, SignalBundle | `interpretation/` | |
| `signal/types.py` | Signal, SignalBundle, SignalTier | `interpretation/` | |
| **strategy/** | | | |
| `strategy/__init__.py` | Docstring | `learning/` | Strategy memory IS learning |
| `strategy/interfaces.py` | StrategyPersistence protocol | `protocols/` | Protocol contract |
| `strategy/memory.py` | StrategyMemory, StrategyStats | `learning/` | |
| **world/** | | | |
| `world/__init__.py` | Docstring | `world_model/` | Rename package |
| `world/calibration.py` | WorldCalibration | `world_model/` | |
| `world/dynamics_adapter.py` | WorldDynamicsAdapter | `world_model/` | |
| `world/model.py` | WorldModel, WorldModelEntry | `world_model/` | |
| `world/reasoning.py` | WorldReasoning | `world_model/` | |
| `world/simulation.py` | WorldSimulation | `world_model/` | |
| `world/state.py` | WorldStateEngine (926 lines, imports eos_ai!) | `world_model/` | **Contaminated** — imports eos_ai |
| `world/substrate.py` | WorldSubstrate | `world_model/` | |
| `world/types.py` | Entity, Relation, Observation, etc. | `world_model/` | |

---

## 2. Naming Mismatches

| Current | Target | Impact |
|---|---|---|
| `world/` | `world_model/` | 8 files, all world/* imports |
| `signal/` | `interpretation/` | 3 files + 1 merge from intent/ |
| `capability/` | `capabilities/` | 3 files |
| `feedback/` | `learning/` | 3 files (+ strategy/ merge) |
| `primitives/` | `ontology/` | 2 files |
| `context/` | `composition/` | 4 files |
| `decision/` | `observability/` | 2 files |
| `intent/` | `interpretation/` (merge with signal) | 2 files |
| `memory/` | `storage/` | 2 files |
| `strategy/` | `learning/` (merge with feedback) | 3 files |

---

## 3. Missing Protocol Contracts

The target architecture requires explicit protocol types in `protocols/`.
Current state and gaps:

| Contract | Exists? | Current Location | Notes |
|---|---|---|---|
| `Signal` | YES | `signal/types.py` | Frozen dataclass, well-defined |
| `InterpretationResult` | PARTIAL | `intent/compiler.py` → `Intent` | Rename `Intent` → `InterpretationResult` |
| `WorldUpdate` | NO | — | World model accepts raw strings, no structured update type |
| `Plan` | PARTIAL | `execution/harness.py` → `HarnessPlan` | Exists but not in protocols/ |
| `CapabilitySpec` | YES | `capability/registry.py` → `Capability` | Well-defined, needs move to protocols/ |
| `AdapterSpec` | PARTIAL | `adapters/base.py` → protocols | Five protocol classes exist, not centralized |
| `ExecutionRequest` | YES | `execution/contract.py` | Well-defined |
| `ExecutionResult` | YES | `execution/contract.py` | Well-defined |
| `Outcome` | PARTIAL | `feedback/loop.py` → `OutcomeType` / `FeedbackEvent` | String constants, not a proper type |
| `FeedbackEvent` | YES | `feedback/loop.py` | Well-defined |
| `GovernanceDecision` | YES | `governance/authority.py` | Well-defined |
| `WorkstationProfile` | NO | — | No workstation profile type exists |
| `BootSequence` | NO | — | No boot/initialization protocol |
| `WorkMode` | NO | — | No work mode type exists |

**Missing contracts to create:**
1. `WorldUpdate` — structured type for world model mutations
2. `WorkstationProfile` — environment detection result type
3. `BootSequence` — initialization order protocol
4. `WorkMode` — operational mode enum (observe, analyze, act, execute)
5. `Outcome` — proper enum (currently string constants in OutcomeType)

---

## 4. Duplicated Responsibilities

| Responsibility | Found In | Resolution |
|---|---|---|
| Authority levels | `governance/authority.py` (AuthorityLevel: 4 levels) AND `governance/capability.py` (CapabilityLevel: 4 levels) | These are related but distinct — AuthorityLevel gates operations, CapabilityLevel gates agents. Keep both in governance/ but document the relationship. |
| Outcome types | `feedback/loop.py` (OutcomeType class with string constants) AND `execution/contract.py` (ExecutionStatus enum) | Consolidate into a single `Outcome` protocol type in protocols/ |
| Performance tracking | `capability/registry.py` (PerformanceStats) AND `strategy/memory.py` (StrategyStats) | Different granularity (capability vs strategy). Keep separate but share a common metric protocol. |
| Singleton management | Every `interfaces.py` file repeats the same get/set/reset/default pattern | Extract a `SingletonProvider[T]` generic into `core/` |
| `_now_ms()` | `run.py`, `execution/engine.py`, `execution/harness.py`, `execution/pipeline.py` | Extract to `core/clock.py` |
| Persistence protocols | `goals/interfaces.py`, `strategy/interfaces.py`, `memory/storage.py`, `execution/interfaces.py`, `capability/registry.py` (PersistenceBackend) | All follow the same pattern. All belong in `protocols/persistence.py` |
| EOS adapter discovery | `goals/interfaces.py`, `strategy/interfaces.py`, `memory/storage.py`, `execution/interfaces.py` | All try `from eos_ai.adapters...` with ImportError fallback. Centralize in `adapters/eos_bridge.py` |

---

## 5. eos_ai Contamination

These are **hard rule violations** — UMH must not import eos_ai:

| File | Import | Severity |
|---|---|---|
| `world/state.py:46` | `from eos_ai.decision_trace import DecisionTrace` | **CRITICAL** — runtime import inside TYPE_CHECKING |
| `world/state.py:47` | `from eos_ai.goal_state import GoalRegistry` | **CRITICAL** — same |
| `world/state.py:329` | `from eos_ai.strategy_memory import get_strategy_memory` | **CRITICAL** — runtime import |
| `goals/interfaces.py:64` | `from eos_ai.adapters.umh_goals import...` | ACCEPTABLE — inside try/except fallback |
| `strategy/interfaces.py:64` | `from eos_ai.adapters.umh_strategy import...` | ACCEPTABLE — inside try/except fallback |
| `memory/storage.py:62` | `from eos_ai.adapters.umh_storage import...` | ACCEPTABLE — inside try/except fallback |
| `execution/interfaces.py:90,115` | `from eos_ai.adapters.umh_execution import...` | ACCEPTABLE — inside try/except fallback |

**world/state.py is the only CRITICAL contamination.** The interfaces files use a legitimate adapter-discovery pattern (try eos_ai, fallback to null). world/state.py imports eos_ai types at class body level — this breaks standalone UMH operation.

---

## 6. Non-UMH Modules for Promotion

| Current Location | Candidate For | Notes |
|---|---|---|
| `eos_ai/adapters/umh_storage.py` | `adapters/eos_storage.py` | EOS storage adapter — stays in eos_ai, bridges via protocol |
| `eos_ai/adapters/umh_execution.py` | `adapters/eos_execution.py` | Same pattern |
| `eos_ai/adapters/umh_goals.py` | `adapters/eos_goals.py` | Same pattern |
| `eos_ai/adapters/umh_strategy.py` | `adapters/eos_strategy.py` | Same pattern |

**Verdict:** These should NOT be promoted into umh/. They are EOS-specific adapter implementations. UMH defines the protocols; EOS implements them. The current try/except bridge pattern in interfaces.py is correct but should be centralized.

---

## 7. Proposed Final UMH Tree

```
umh/
├── __init__.py                    # Public API: from umh import run
├── core/
│   ├── __init__.py
│   ├── run.py                     # The 9-stage control plane spine
│   ├── clock.py                   # _now_ms() and time utilities
│   └── event_bus.py               # EventBus, EventRegistry (from signal/)
│
├── protocols/
│   ├── __init__.py
│   ├── signals.py                 # Signal, SignalBundle, SignalTier
│   ├── interpretation.py          # Intent (→ InterpretationResult)
│   ├── execution.py               # ExecutionRequest, ExecutionResult, ExecutionContext
│   ├── capabilities.py            # Capability, CapabilitySpec
│   ├── adapters.py                # LLMAdapter, ShellAdapter, etc. protocols
│   ├── governance.py              # GovernanceDecision, AuthorityLevel
│   ├── persistence.py             # StorageBackend, GoalPersistence, StrategyPersistence, etc.
│   ├── outcome.py                 # Outcome enum, FeedbackEvent
│   └── planning.py                # GoalState, HarnessPlan contracts
│
├── ontology/
│   ├── __init__.py
│   └── primitives.py              # PrimitiveTag, L0, validation
│
├── interpretation/
│   ├── __init__.py
│   ├── ingest.py                  # classify_input
│   └── compiler.py                # compile_intent
│
├── world_model/
│   ├── __init__.py
│   ├── types.py                   # Entity, Relation, Observation, etc.
│   ├── model.py                   # WorldModel, WorldModelEntry
│   ├── substrate.py               # WorldSubstrate
│   ├── reasoning.py               # WorldReasoning
│   ├── simulation.py              # WorldSimulation
│   ├── calibration.py             # WorldCalibration
│   ├── dynamics_adapter.py        # WorldDynamicsAdapter
│   └── state.py                   # WorldStateEngine (DECONTAMINATED)
│
├── planning/
│   ├── __init__.py
│   ├── goals.py                   # GoalState, GoalRegistry, GoalTracker
│   ├── objective.py               # ObjectiveFunction, ObjectiveSet
│   └── engine.py                  # GoalEngineState, weight adaptation
│
├── composition/
│   ├── __init__.py
│   ├── types.py                   # ContextPriority, ContextSection, ContextResult
│   ├── budget.py                  # TokenBudget
│   └── builder.py                 # ContextBuilder
│
├── capabilities/
│   ├── __init__.py
│   ├── registry.py                # CapabilityRegistry, PerformanceStats
│   └── router.py                  # route_to_capability, RoutingDecision
│
├── adapters/
│   ├── __init__.py
│   ├── llm.py                     # OllamaLLMAdapter, HttpLLMAdapter
│   ├── null.py                    # All null/stub implementations
│   └── bridge.py                  # Centralized EOS adapter discovery
│
├── execution/
│   ├── __init__.py
│   ├── engine.py                  # execute() single entry point
│   ├── harness.py                 # AgentHarness, multi-step orchestration
│   ├── pipeline.py                # ExecutionPipeline, composable stages
│   ├── stages.py                  # StageContext, ExecutionStage protocol
│   └── quality.py                 # QualityGate
│
├── governance/
│   ├── __init__.py
│   ├── authority.py               # AuthorityLevel, check_governance
│   ├── capability.py              # CapabilityEnforcer, ProfileRegistry
│   └── governor.py                # ImprovementProposal, Governor
│
├── learning/
│   ├── __init__.py
│   ├── feedback.py                # record_outcome, FeedbackEvent
│   ├── dynamics.py                # FeedbackDynamics, delayed scores
│   └── strategy.py                # StrategyMemory, StrategyStats
│
├── observability/
│   ├── __init__.py
│   └── trace.py                   # DecisionTrace
│
├── interface/
│   ├── __init__.py
│   └── cli.py                     # __main__.py contents
│
├── storage/
│   ├── __init__.py
│   └── backend.py                 # StorageBackend, InMemoryStorage
│
└── tests/
    ├── __init__.py
    ├── test_interpretation.py
    ├── test_world_model.py
    ├── test_capabilities.py
    ├── test_execution.py
    ├── test_governance.py
    ├── test_learning.py
    ├── test_composition.py
    └── test_run.py
```

**Subsystems from target list NOT created (with reasoning):**

| Target Subsystem | Decision | Reason |
|---|---|---|
| `environments/` | SKIP | No environment-specific logic exists yet. When it does, it goes here. |
| `workstation/` | SKIP | Only a NullWorkstationAdapter exists. Not enough for a subsystem. |
| `registry/` | ABSORBED into `capabilities/` and `governance/` | CapabilityRegistry and ProfileRegistry are domain-specific, not generic. |
| `security/` | ABSORBED into `governance/` | Capability enforcement IS the security layer. |

---

## 8. Hard Rule Verification

| Rule | Current Compliance | Action Required |
|---|---|---|
| No execution logic outside `execution/` | **VIOLATED** — `run.py:378-401` has `_execute_via_adapter()` | Move to `execution/engine.py` |
| No capability logic outside `capabilities/` | **OK** — all in `capability/` | Rename package |
| No adapter invocation outside `adapters/` | **VIOLATED** — `run.py:397` calls `get_adapter("llm")` directly | Route through execution/ |
| No governance bypass | **OK** — `run.py:187-208` gates on governance | Keep |
| No direct external tool calls | **OK** — all go through adapters | Keep |
| No memory writes outside memory/world_model/storage APIs | **VIOLATED** — `feedback/loop.py` writes to module-level `_feedback_log` | Move to storage-backed persistence |
| No UI logic inside core intelligence | **OK** — CLI is separate in `__main__.py` | Move to `interface/` |

---

## 9. Exact Migration Sequence

### Wave 0: Decontaminate (no file moves)
1. **Fix `world/state.py`** — remove all `from eos_ai` imports.
   Replace with protocol-based injection or move the state extraction
   to accept pre-extracted dicts instead of importing eos_ai types directly.

### Wave 1: Create infrastructure (new files only)
2. Create `core/__init__.py`
3. Create `core/clock.py` — extract `_now_ms()` from 4 files
4. Create `protocols/__init__.py`
5. Create `protocols/persistence.py` — consolidate 5 persistence patterns
6. Create `adapters/bridge.py` — centralize EOS adapter discovery
7. Create `adapters/null.py` — consolidate all null stubs from `adapters/base.py`

### Wave 2: Rename packages (simple moves, update imports)
8. `primitives/` → `ontology/`
9. `signal/` → `interpretation/` (keep event_bus separate)
10. `intent/` → merge into `interpretation/`
11. `capability/` → `capabilities/`
12. `context/` → `composition/`
13. `decision/` → `observability/`
14. `feedback/` → `learning/`
15. `strategy/` → merge into `learning/`
16. `memory/` → `storage/`
17. `world/` → `world_model/`

### Wave 3: Structural moves
18. Move `signal/event_bus.py` → `core/event_bus.py`
19. Move `__main__.py` → `interface/cli.py` (update `__main__.py` to import)
20. Move `run.py` → `core/run.py` (update `__init__.py`)
21. Move execution contracts to `protocols/execution.py`
22. Move adapter protocols to `protocols/adapters.py`
23. Extract `_execute_via_adapter()` from run.py into `execution/`

### Wave 4: Create missing contracts
24. Create `WorldUpdate` type in `protocols/`
25. Create `Outcome` proper enum in `protocols/outcome.py`
26. Create `BootSequence` protocol in `protocols/`
27. Create `WorkMode` enum in `protocols/`

### Wave 5: Import fixup + verification
28. Global find-replace all `from umh.signal.` → `from umh.interpretation.`
29. Global find-replace all `from umh.capability.` → `from umh.capabilities.`
30. Global find-replace all `from umh.context.` → `from umh.composition.`
31. Global find-replace all `from umh.decision.` → `from umh.observability.`
32. Global find-replace all `from umh.feedback.` → `from umh.learning.`
33. Global find-replace all `from umh.strategy.` → `from umh.learning.`
34. Global find-replace all `from umh.memory.` → `from umh.storage.`
35. Global find-replace all `from umh.world.` → `from umh.world_model.`
36. Global find-replace all `from umh.intent.` → `from umh.interpretation.`
37. Global find-replace all `from umh.primitives.` → `from umh.ontology.`
38. Run `python3 -c "from umh import run; print('OK')"` to verify
39. Run all existing tests (currently in `_holding/runtime_legacy/tests/`)

### Wave 6: Compatibility shims (temporary)
40. Add re-export shims in old package locations for any external consumers
41. Mark shims with deprecation warnings

---

## 10. Risky Moves

| Risk | Impact | Mitigation |
|---|---|---|
| `world/state.py` decontamination | 926-line file with eos_ai imports at runtime | Must refactor to accept dicts/protocols instead of eos_ai types. Test thoroughly. |
| `signal/` + `intent/` merge into `interpretation/` | Two packages becoming one. Both have `__init__.py` re-exports. | Keep internal file names (ingest.py, compiler.py). Only package name changes. |
| `feedback/` + `strategy/` merge into `learning/` | Two packages becoming one. Different persistence patterns. | Keep internal file names (feedback.py, dynamics.py, strategy.py). |
| `DecisionTrace` in `observability/` | 1066-line file with 200+ fields. Any consumer importing from `decision.trace` breaks. | This is the most-imported type. Shim required during transition. |
| `run.py` → `core/run.py` | Changes the primary import path `from umh.run import run` | `umh/__init__.py` must re-export from new location. Shim the old path. |
| `execution/contract.py` → `protocols/execution.py` | Well-established import path in execution/ and harness/ | Keep execution/-internal imports working via re-export. |
| External consumers in `_holding/runtime_legacy/` | 50+ files import from umh.* | These are legacy holding files. Low risk — update or ignore. |

---

## 11. Subsystem Dependency Graph (Post-Migration)

```
ontology/           ← no dependencies (foundation)
    ↓
protocols/          ← depends on ontology/ only
    ↓
interpretation/     ← depends on protocols/
    ↓
world_model/        ← depends on protocols/
    ↓
planning/           ← depends on protocols/
    ↓
composition/        ← depends on protocols/
    ↓
capabilities/       ← depends on protocols/
    ↓
governance/         ← depends on protocols/, capabilities/
    ↓
execution/          ← depends on protocols/, capabilities/, governance/, adapters/
    ↓
learning/           ← depends on protocols/, capabilities/
    ↓
observability/      ← depends on protocols/ (pure data, no upstream deps)
    ↓
adapters/           ← depends on protocols/ only
    ↓
storage/            ← depends on protocols/ only
    ↓
core/               ← depends on everything above (orchestration)
    ↓
interface/          ← depends on core/ only
```

**No circular dependencies in this graph.**

---

## Summary

- **55 current files** → **~50 files** across **15 active subsystems** + tests/
- **4 naming mismatches** fixed (world→world_model, signal→interpretation, capability→capabilities, feedback→learning)
- **3 hard rule violations** to fix before any file moves
- **5 missing protocol contracts** to create
- **7 duplicated responsibilities** to consolidate
- **1 critical eos_ai contamination** in world/state.py
- **6-wave migration sequence** — decontaminate → create infrastructure → rename → restructure → create contracts → fixup imports
