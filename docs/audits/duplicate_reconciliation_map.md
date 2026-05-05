# Duplicate Reconciliation Map

Generated: 2026-04-26

## Summary

| Category | Count |
|---|---|
| **Total duplicate pairs** | 45 |
| **Unique files with duplicates** | 41 (4 files exist in 3 locations) |
| IDENTICAL (import-path-only diff) | 15 |
| DIVERGED_MINOR (import paths only) | 16 |
| DIVERGED_SIGNIFICANT (different code/purpose) | 7 |
| IDENTICAL_EXACT (byte-identical) | 15 |
| DIVERGED_MINOR (only import paths differ) | 16 |

### Triple-copy files

4 files exist in 3 locations (runtime_engine + 2 modular dirs):

| File | Locations | Notes |
|---|---|---|
| calibration.py | runtime_engine (344L), world (565L), reasoning (344L) | world version is a **different module** (WorldCalibration); RE/reasoning are import-path variants |
| memory.py | runtime_engine (1024L), protocols (31L), strategy (395L) | All 3 are **different modules** sharing a filename |
| persistence.py | runtime_engine (754L), protocols (8L), persistence_layer (754L) | protocols is a **different module** (protocol contracts); RE/persistence_layer are byte-identical |
| plan_mutation.py | runtime_engine (764L), planning (764L), substrate (463L) | substrate is a **different module** (event-native mutation); RE/planning are import-path variants |

---

## Full Classification Table

### Legend

- **RE** = `umh/runtime_engine/`
- **MOD** = modular directory version
- **RE-imp** = number of import sites referencing the runtime_engine version
- **MOD-imp** = number of import sites referencing the modular version
- **Class** = classification (see definitions below table)
- **Keep** = recommended canonical location (for IDENTICAL/DIVERGED_MINOR only)

---

### Pair-by-pair analysis

| # | File | RE path | MOD path | Identical? | Diff description | RE-imp | MOD-imp | Class | Keep |
|---|---|---|---|---|---|---|---|---|---|
| 1 | adaptive_exploration.py | runtime_engine/ | analytics/ | No | Self-import path only (1 line) | 2 | 4 | DIVERGED_MINOR | analytics |
| 2 | calibration.py | runtime_engine/ | reasoning/ | No | Self-import + 3 persistence import paths | 2 | 2 | DIVERGED_MINOR | reasoning |
| 3 | calibration.py | runtime_engine/ | world/ | No | **Completely different module** (WorldCalibration vs CalibrationEngine, 565 vs 344 lines) | 2 | 6 | NOT_DUPLICATE | both (different modules) |
| 4 | causal_attribution.py | runtime_engine/ | reasoning/ | No | Self-import path only (1 line) | 1 | 2 | DIVERGED_MINOR | reasoning |
| 5 | causal_credit.py | runtime_engine/ | reasoning/ | No | 1 import path (hierarchical_planning) | 0 | 1 | DIVERGED_MINOR | reasoning |
| 6 | causal_memory.py | runtime_engine/ | reasoning/ | Yes | Byte-identical | 2 | 1 | IDENTICAL_SAFE | runtime_engine |
| 7 | context_engine.py | runtime_engine/ | reasoning/ | Yes | Byte-identical | 2 | 4 | IDENTICAL_SAFE | reasoning |
| 8 | control_layer.py | runtime_engine/ | reasoning/ | No | 4 import paths (self, calibration, decision_trace, goal_mode) | 1 | 2 | DIVERGED_MINOR | reasoning |
| 9 | convergence.py | runtime_engine/ | reasoning/ | No | 2 import paths (self-import, decision_trace) | 1 | 3 | DIVERGED_MINOR | reasoning |
| 10 | counterfactual_eval.py | runtime_engine/ | reasoning/ | No | 7 import paths (self, decision_trace, meta_goal, goal_validator x3, goal_alignment) | 1 | 2 | DIVERGED_MINOR | reasoning |
| 11 | credit_assignment.py | runtime_engine/ | reasoning/ | Yes | Byte-identical | 2 | 1 | IDENTICAL_SAFE | runtime_engine |
| 12 | directive_engine.py | runtime_engine/ | planning/ | Yes | Byte-identical | 0 | 1 | IDENTICAL_SAFE + ORPHAN(RE) | planning |
| 13 | event_bus.py | runtime_engine/ | signal/ | No | **Significantly different.** RE version (424L) is EOS-specific wrapper importing from signal/ version (225L). signal/ is the generic bus. | 8 | 3 | DIVERGED_SIGNIFICANT | both (wrapper + base) |
| 14 | execution_router.py | runtime_engine/ | substrate/ | No | **Completely different module.** RE (271L) is action-dispatch router. substrate/ (219L) is data-driven routing-decision engine. | 5 | 3 | NOT_DUPLICATE | both (different modules) |
| 15 | exploration_engine.py | runtime_engine/ | analytics/ | No | 1 import path (score_distribution) | 3 | 1 | DIVERGED_MINOR | runtime_engine |
| 16 | fabric_analytics.py | runtime_engine/ | analytics/ | No | 1 import path (memory_fabric) | 0 | 1 | DIVERGED_MINOR + ORPHAN(RE) | analytics |
| 17 | foresight_engine.py | runtime_engine/ | policy/ | Yes | Byte-identical | 1 | 1 | IDENTICAL_SAFE | policy |
| 18 | hierarchical_planning.py | runtime_engine/ | planning/ | No | 4 import paths (self, decision_trace, persistence x2) | 7 | 12 | DIVERGED_MINOR + BOTH_IMPORTED | planning |
| 19 | influence_orchestrator.py | runtime_engine/ | reasoning/ | No | Self-import path only (1 line) | 1 | 3 | DIVERGED_MINOR | reasoning |
| 20 | influence_scoring.py | runtime_engine/ | reasoning/ | Yes | Byte-identical | 0 | 4 | IDENTICAL_SAFE + ORPHAN(RE) | reasoning |
| 21 | memory.py | runtime_engine/ | protocols/ | No | **Completely different module.** RE (1024L) is Neon-backed AgentMemory. protocols/ (31L) is memory protocol contracts. | 37 | 0 | NOT_DUPLICATE | both (different modules) |
| 22 | memory.py | runtime_engine/ | strategy/ | No | **Completely different module.** RE (1024L) is AgentMemory. strategy/ (395L) is StrategyMemory. | 37 | 17 | NOT_DUPLICATE | both (different modules) |
| 23 | memory_fabric.py | runtime_engine/ | persistence_layer/ | No | 2 import paths (self-import, persistence) | 2 | 5 | DIVERGED_MINOR | persistence_layer |
| 24 | meta_control.py | runtime_engine/ | reasoning/ | Yes | Byte-identical | 0 | 1 | IDENTICAL_SAFE + ORPHAN(RE) | reasoning |
| 25 | meta_generalization.py | runtime_engine/ | reasoning/ | Yes | Byte-identical | 2 | 1 | IDENTICAL_SAFE | runtime_engine |
| 26 | meta_goal.py | runtime_engine/ | goals/ | No | 2 import paths (self-import, decision_trace) | 8 | 10 | DIVERGED_MINOR + BOTH_IMPORTED | goals |
| 27 | meta_weight_engine.py | runtime_engine/ | reasoning/ | No | 1 import path (persistence) | 0 | 3 | DIVERGED_MINOR + ORPHAN(RE) | reasoning |
| 28 | model_router.py | runtime_engine/ | adapters/ | No | **Significantly different.** RE (415L) is EOS wrapper that re-exports from adapters/. adapters/ (636L) is the generic routing engine. | 12 | 2 | DIVERGED_SIGNIFICANT | both (wrapper + base) |
| 29 | outcome_evaluator.py | runtime_engine/ | feedback/ | No | 2 import paths (self-import, signal_router) | 2 | 3 | DIVERGED_MINOR | feedback |
| 30 | outcome_feedback.py | runtime_engine/ | feedback/ | No | Self-import path only (1 line) | 1 | 3 | DIVERGED_MINOR | feedback |
| 31 | pattern_engine.py | runtime_engine/ | analytics/ | No | 2 import paths (self-import x2) | 2 | 5 | DIVERGED_MINOR | analytics |
| 32 | persistence.py | runtime_engine/ | persistence_layer/ | Yes | Byte-identical | 13 | 7 | IDENTICAL_SAFE + BOTH_IMPORTED | persistence_layer |
| 33 | persistence.py | runtime_engine/ | protocols/ | No | **Completely different module.** RE (754L) is full persistence engine. protocols/ (8L) is protocol contract stubs. | 13 | 5 | NOT_DUPLICATE | both (different modules) |
| 34 | plan_mutation.py | runtime_engine/ | planning/ | No | 6 import paths (self-import, hierarchical_planning x5) | 1 | 2 | DIVERGED_MINOR | planning |
| 35 | plan_mutation.py | runtime_engine/ | substrate/ | No | **Completely different module.** RE (764L) is deterministic plan evolution. substrate/ (463L) is event-native mutation with causal transforms. | 1 | 2 | NOT_DUPLICATE | both (different modules) |
| 36 | regime_engine.py | runtime_engine/ | policy/ | Yes | Byte-identical | 2 | 0 | IDENTICAL_SAFE + ORPHAN(MOD) | runtime_engine |
| 37 | risk_model.py | runtime_engine/ | policy/ | Yes | Byte-identical | 2 | 0 | IDENTICAL_SAFE + ORPHAN(MOD) | runtime_engine |
| 38 | score_distribution.py | runtime_engine/ | analytics/ | Yes | Byte-identical | 1 | 1 | IDENTICAL_SAFE | analytics |
| 39 | signal_orchestrator.py | runtime_engine/ | analytics/ | Yes | Byte-identical | 1 | 1 | IDENTICAL_SAFE | analytics |
| 40 | stability_guard.py | runtime_engine/ | policy/ | Yes | Byte-identical | 1 | 1 | IDENTICAL_SAFE | policy |
| 41 | strategy_mutation.py | runtime_engine/ | analytics/ | No | Self-import path only (1 line) | 1 | 2 | DIVERGED_MINOR | analytics |
| 42 | strategy_pattern_memory.py | runtime_engine/ | analytics/ | Yes | Byte-identical | 0 | 2 | IDENTICAL_SAFE + ORPHAN(RE) | analytics |
| 43 | system_graph.py | runtime_engine/ | execution/ | No | 3 import paths (self-import, execution_router x2) | 2 | 1 | DIVERGED_MINOR | execution |
| 44 | system_registry.py | runtime_engine/ | execution/ | No | Self-import path only (1 line) | 2 | 1 | DIVERGED_MINOR | execution |
| 45 | system_selector.py | runtime_engine/ | execution/ | No | Self-import path only (1 line) | 2 | 1 | DIVERGED_MINOR | execution |

---

## Classification Definitions

| Class | Meaning |
|---|---|
| **IDENTICAL_SAFE** | Byte-identical. One copy can be deleted; keep the one with more importers. |
| **DIVERGED_MINOR** | Only import path strings differ. Same logic, same API. Can be reconciled by choosing one and fixing imports. |
| **DIVERGED_SIGNIFICANT** | Real code differences: different architecture, different API, or wrapper-over-base relationship. Cannot simply delete one. |
| **NOT_DUPLICATE** | Same filename but completely different modules (different classes, different purpose). Not actually duplicates. |
| **ORPHAN(RE)** | The runtime_engine copy has 0 importers. Safe to remove. |
| **ORPHAN(MOD)** | The modular copy has 0 importers. Safe to remove. |
| **BOTH_IMPORTED** | Both versions have active importers. Requires import migration before deletion. |

---

## Adjusted Counts (excluding NOT_DUPLICATE pairs)

After removing 7 NOT_DUPLICATE pairs (same filename, different module), the true duplicate count is:

| Category | Count |
|---|---|
| True duplicates (same code, two locations) | 38 |
| IDENTICAL_SAFE | 15 |
| DIVERGED_MINOR (import paths only) | 16 |
| DIVERGED_SIGNIFICANT (wrapper/base pattern) | 2 (event_bus, model_router) |
| NOT_DUPLICATE (different modules) | 7 |

---

## IDENTICAL Pairs: Canonical Location Decision

| File | Keep | Remove | RE importers | MOD importers | Migration needed |
|---|---|---|---|---|---|
| causal_memory.py | runtime_engine | reasoning | 2 | 1 | Fix 1 importer |
| context_engine.py | reasoning | runtime_engine | 2 | 4 | Fix 2 importers |
| credit_assignment.py | runtime_engine | reasoning | 2 | 1 | Fix 1 importer |
| directive_engine.py | planning | runtime_engine | 0 | 1 | None (RE is orphan) |
| foresight_engine.py | policy | runtime_engine | 1 | 1 | Fix 1 importer |
| influence_scoring.py | reasoning | runtime_engine | 0 | 4 | None (RE is orphan) |
| meta_control.py | reasoning | runtime_engine | 0 | 1 | None (RE is orphan) |
| meta_generalization.py | runtime_engine | reasoning | 2 | 1 | Fix 1 importer |
| persistence.py | persistence_layer | runtime_engine | 13 | 7 | Fix 13 importers |
| regime_engine.py | runtime_engine | policy | 2 | 0 | None (MOD is orphan) |
| risk_model.py | runtime_engine | policy | 2 | 0 | None (MOD is orphan) |
| score_distribution.py | analytics | runtime_engine | 1 | 1 | Fix 1 importer |
| signal_orchestrator.py | analytics | runtime_engine | 1 | 1 | Fix 1 importer |
| stability_guard.py | policy | runtime_engine | 1 | 1 | Fix 1 importer |
| strategy_pattern_memory.py | analytics | runtime_engine | 0 | 2 | None (RE is orphan) |

**Total import migrations needed for IDENTICAL pairs: ~22 import statements**

---

## DIVERGED_SIGNIFICANT Pairs: Architecture Notes

### 1. event_bus.py (RE 424L vs signal/ 225L)

**Pattern: Wrapper over base.**

- `umh/signal/event_bus.py` is the pure, generic EventBus (no DB imports, no EOS concepts)
- `umh/runtime_engine/event_bus.py` imports from signal/ and adds: NeonEventLogger, EOS event type constants, EOSEventRegistry, EOS-specific handlers, `get_bus()` singleton
- Both should exist. This is intentional layering: generic bus + EOS specialization.
- **Action: No deduplication needed.** Rename RE version to something like `eos_event_bus.py` to eliminate filename collision confusion.

### 2. model_router.py (RE 415L vs adapters/ 636L)

**Pattern: Wrapper over base.**

- `umh/adapters/model_router.py` is the generic multi-provider routing engine (no umh imports, standalone)
- `umh/runtime_engine/model_router.py` is the EOS compatibility wrapper: re-exports everything from adapters/, adds CC SDK backend, Claude CLI tmux backend, Discord mode, CEO keyword detection
- Both should exist. The RE version explicitly imports from adapters/.
- **Action: No deduplication needed.** Same wrapper pattern as event_bus. Consider renaming RE version to `eos_model_router.py`.

---

## NOT_DUPLICATE Pairs: Same Filename, Different Module

These 7 pairs share a filename but are architecturally distinct modules. No reconciliation needed.

| File | Location A | Location B | Why different |
|---|---|---|---|
| calibration.py | runtime_engine (CalibrationEngine, threshold tuning) | world (WorldCalibration, prediction-vs-reality error) | Different domain, different classes, different API |
| memory.py | runtime_engine (AgentMemory, Neon-backed interaction log) | protocols (memory protocol contracts, 31L) | Protocol interface vs implementation |
| memory.py | runtime_engine (AgentMemory, 1024L) | strategy (StrategyMemory, strategy scoring, 395L) | Completely different data model |
| persistence.py | runtime_engine (full persistence engine, 754L) | protocols (protocol contracts, 8L) | Protocol interface vs implementation |
| execution_router.py | runtime_engine (action-dispatch handler routing) | substrate (data-driven routing-decision engine) | Different architecture, different API |
| plan_mutation.py | runtime_engine (6-operation plan evolution engine) | substrate (causal+structural transform engine, event-native) | Different mutation strategies, different API |

---

## Recommended Reconciliation Order

Ordered by safety (easiest/safest first):

### Phase 1: Delete orphaned identical copies (0 import migration)

Risk: ZERO. These copies have no importers.

| Action | File |
|---|---|
| Delete RE copy | directive_engine.py (RE has 0 importers) |
| Delete RE copy | influence_scoring.py (RE has 0 importers) |
| Delete RE copy | meta_control.py (RE has 0 importers) |
| Delete RE copy | strategy_pattern_memory.py (RE has 0 importers) |
| Delete MOD copy | regime_engine.py (policy/ has 0 importers) |
| Delete MOD copy | risk_model.py (policy/ has 0 importers) |

**6 files deleted, 0 import changes.**

### Phase 2: Delete identical copies with minimal import migration (1-2 importers to fix)

Risk: LOW. Mechanical import path changes.

| Action | File | Importers to fix |
|---|---|---|
| Keep reasoning, delete RE | context_engine.py | 2 |
| Keep RE, delete reasoning | causal_memory.py | 1 |
| Keep RE, delete reasoning | credit_assignment.py | 1 |
| Keep RE, delete reasoning | meta_generalization.py | 1 |
| Keep policy, delete RE | foresight_engine.py | 1 |
| Keep analytics, delete RE | score_distribution.py | 1 |
| Keep analytics, delete RE | signal_orchestrator.py | 1 |
| Keep policy, delete RE | stability_guard.py | 1 |

**8 files deleted, 9 import changes.**

### Phase 3: Delete identical copy with heavy import migration

Risk: MEDIUM. Many import statements to update but purely mechanical.

| Action | File | Importers to fix |
|---|---|---|
| Keep persistence_layer, delete RE | persistence.py | 13 |

**1 file deleted, 13 import changes.**

### Phase 4: Reconcile DIVERGED_MINOR pairs (import-path-only diffs)

Risk: LOW-MEDIUM. Pick canonical version (the modular one), delete the other, fix importers.

For each pair, the modular version has the correct internal import paths already.
The runtime_engine version has stale internal import paths pointing back to runtime_engine.
**Always keep the modular version** (it has the forward-looking import paths).

Ordered by importer count (fewest first):

| Keep | Delete | Importers to migrate |
|---|---|---|
| analytics/fabric_analytics.py | RE version | 0 (RE is orphan) |
| reasoning/meta_weight_engine.py | RE version | 0 (RE is orphan) |
| reasoning/causal_credit.py | RE version | 0 (RE is orphan) |
| feedback/outcome_feedback.py | RE version | 1 |
| reasoning/convergence.py | RE version | 1 |
| reasoning/counterfactual_eval.py | RE version | 1 |
| reasoning/control_layer.py | RE version | 1 |
| reasoning/causal_attribution.py | RE version | 1 |
| analytics/strategy_mutation.py | RE version | 1 |
| reasoning/influence_orchestrator.py | RE version | 1 |
| planning/plan_mutation.py | RE version | 1 |
| reasoning/calibration.py | RE version | 2 (includes control_layer self-ref) |
| analytics/adaptive_exploration.py | RE version | 2 |
| feedback/outcome_evaluator.py | RE version | 2 |
| analytics/pattern_engine.py | RE version | 2 |
| persistence_layer/memory_fabric.py | RE version | 2 |
| execution/system_selector.py | RE version | 2 |
| execution/system_registry.py | RE version | 2 |
| execution/system_graph.py | RE version | 2 |
| analytics/exploration_engine.py | RE version | 3 |
| goals/meta_goal.py | RE version | 8 |
| planning/hierarchical_planning.py | RE version | 7 |

**Total: 16 files deleted, ~44 import statements to fix.**

### Phase 5: Rename DIVERGED_SIGNIFICANT wrappers (optional)

Risk: LOW (rename only, does not change behavior).

| Action | Current | Proposed |
|---|---|---|
| Rename | runtime_engine/event_bus.py | runtime_engine/eos_event_bus.py |
| Rename | runtime_engine/model_router.py | runtime_engine/eos_model_router.py |

Would require updating their 8 and 12 importers respectively.
**Optional but eliminates filename confusion.**

---

## Risk Assessment

### Overall risk: LOW-MEDIUM

The vast majority of duplicates (31 of 38 true pairs) are either byte-identical or differ only in import path strings. The reconciliation is mechanical:

1. **No logic changes needed** for any pair except the 2 DIVERGED_SIGNIFICANT wrappers (which should be kept as-is)
2. **All import migrations are grep-replaceable** -- every change is `from umh.runtime_engine.X import` -> `from umh.{modular_dir}.X import`
3. **7 "duplicates" are not duplicates at all** -- same filename, different module. No action needed.

### Key risks to watch

| Risk | Mitigation |
|---|---|
| Missing an import reference (grep miss) | Run `python3 -c "import umh.runtime_engine.X"` after each deletion to verify no broken references |
| Tests importing old paths | Grep `tests/` separately for each migrated module |
| Dynamic imports (string-based) | Grep for `importlib` and `__import__` referencing runtime_engine modules |
| Circular import introduced by path change | Each modular version already works with its internal import paths, so this is unlikely |

### Total impact

- **31 files to delete** (15 identical + 16 diverged-minor)
- **~66 import statements to update** across the codebase
- **7 filename collisions to ignore** (different modules)
- **2 wrapper/base pairs to optionally rename** for clarity
- **0 logic changes required**

### Direction of migration

The clear architectural intent is: **runtime_engine/ files should migrate to modular directories.**

- 22 of 31 deletable files are RE copies (modular version is canonical)
- 9 of 31 deletable files are modular copies (RE version has more importers and no modular equivalent yet)
- The modular versions consistently use forward-looking import paths (e.g., `umh.persistence_layer.persistence` instead of `umh.runtime_engine.persistence`)
- The runtime_engine versions use stale internal import paths pointing back into runtime_engine
