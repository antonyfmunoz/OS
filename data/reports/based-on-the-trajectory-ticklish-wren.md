# Campaign 12 — Learning Intelligence & Outcome Compounding

## Context

Campaigns 5-11 built a complete awareness and execution model: Reality (C5) → Operations (C6) → Strategy (C7) → Goals (C8) → Decisions (C9) → Capabilities (C10) → Work (C11). UMH can now answer what exists, what's happening, what matters, what we're trying to achieve, why, what we can do, and what should execute next.

**The gap: What did we learn?** No subsystem synthesizes completed outcomes, validated/invalidated assumptions, decision consequences, and capability evidence into reusable institutional learning. C12 creates the learning-to-compounding loop that closes the cognitive cycle.

**Critical constraint from user spec**: C12 does not create a new memory system. Memory already exists (OutcomeLearningLoop, StrategicMemoryEngine, DecisionRegistry, etc.). C12 converts memory into learning — pattern detection, validated lessons, capability evolution, and portfolio health.

## Key Design Decision: 6 → 5 Sub-Phases

The user spec proposed 6 sub-phases. Exploration revealed:

| Original Spec | Disposition | Reason |
|---|---|---|
| C12.0 Learning Extraction | **Kept → C12.0** | Genuine new value: cross-subsystem semantic lesson extraction |
| C12.1 Outcome Attribution | **Merged → C12.1** | Attribution IS pattern detection applied to outcomes |
| C12.2 Pattern Intelligence | **Merged → C12.1** | Combined as OutcomePatternEngine — attribution + correlation + pattern detection |
| C12.3 Capability Evolution | **Kept → C12.2** | Distinct intelligence: capability trajectories over time |
| C12.4 Learning Portfolio | **Kept → C12.3** | Composition façade (same role as WorkPortfolioRuntime in C11) |
| C12.5 Cockpit | **Kept → C12.4** | Standard cockpit pattern + integration touches |

**OutcomeLearningLoop** (`substrate/organism/outcome_learning.py`) already exists and is heavily integrated (daemon.py, plan_execution_adapter.py, propagation_wiring.py, organism_bridge.py). C12.0 composes it — never replaces or duplicates it. OutcomeLearningLoop handles mechanical outcome→reliability; C12.0 adds semantic lesson extraction on top.

---

## C12.0 — LearningExtractionRuntime

**File**: `substrate/organism/learning_extraction_runtime.py` (~500 LOC)

**New types** (register in `canonical_types.py`):
- `LessonCategory(str, Enum)` — SUCCESS_PATTERN, FAILURE_PATTERN, ASSUMPTION_INVALIDATION, DECISION_CONSEQUENCE, CAPABILITY_GAP, PROCESS_IMPROVEMENT
- `ExtractedLesson` dataclass — id, category, title, description, evidence_sources, confidence, related_decision_ids, related_goal_ids, related_capability_ids, extracted_at, actionable
- `LessonExtractionSnapshot` dataclass — lessons, category_distribution, extraction_velocity, staleness_score

**Composes**:
- `OutcomeLearningLoop` — recent_outcomes(), recent_signals(), get_reliability(), get_adjustments()
- `DecisionRegistry` — active_decisions(), decisions_for_goal()
- `AssumptionTrackingRuntime` — invalidated(), assumptions_for_decision()
- `OutcomeTrackingRuntime` — goals_at_risk(), progress(), health()
- `StrategicMemoryEngine` — detect_patterns(), synthesize()

**Public API**: extract_from_outcome(), extract_from_decision(), extract_batch(), recent_lessons(), lessons_by_category(), actionable_lessons(), snapshot(), summary(), health()

**Persistence**: JSONL at `data/umh/learning/lessons.jsonl`

**Logic**: Cross-references outcome records against decision lineage for causation detection. Correlates failed outcomes with invalidated assumptions. Identifies capability gaps from repeated failures in OutcomeLearningLoop reliability data. Deduplicates by evidence fingerprint.

---

## C12.1 — OutcomePatternEngine

**File**: `substrate/organism/outcome_pattern_engine.py` (~550 LOC)

**New types**:
- `PatternType(str, Enum)` — RECURRING_SUCCESS, RECURRING_FAILURE, DECISION_CORRELATION, CAPABILITY_BOTTLENECK, ASSUMPTION_CHAIN_FAILURE, GOAL_DRIFT_PATTERN, VELOCITY_TREND
- `DetectedPattern` dataclass — id, pattern_type, title, description, evidence, occurrences, first_seen, last_seen, confidence, affected_goals, affected_decisions, affected_capabilities, recommendation
- `AttributionLink` dataclass — source_type, source_id, target_type, target_id, strength, evidence
- `PatternSnapshot` dataclass — patterns, attribution_links, top_correlations, pattern_velocity

**Composes**:
- `LearningExtractionRuntime` (C12.0) — recent_lessons(), lessons_by_category()
- `DecisionLineageEngine` — trace(), blast_radius(), full_chain()
- `DecisionValidityEngine` — at_risk(), invalid()
- `DecisionImpactEngine` — highest_impact()
- `OutcomeLearningLoop` — recent_outcomes(), get_reliability()
- `CompoundingEngine` — detect_outcome_to_insight(), compounding_report()
- `GoalHierarchyEngine` — descendants(), ancestors()

**Public API**: detect_patterns(), attribute_outcome(), correlations(), patterns_for_goal(), patterns_for_capability(), patterns_by_type(), top_patterns(), snapshot(), summary(), health()

**Persistence**: JSONL at `data/umh/learning/patterns.jsonl`

**Logic**: Sliding window pattern detection (groups outcomes by action_type + decision lineage, 3+ occurrences = pattern). Attribution traces outcomes backward through decision lineage, scores by proximity. Cross-tabulates outcome success rates against capability maturity and decision validity.

---

## C12.2 — CapabilityEvolutionEngine

**File**: `substrate/organism/capability_evolution_engine.py` (~450 LOC)

**New types**:
- `EvolutionEventType(str, Enum)` — MATURITY_ADVANCE, MATURITY_DECLINE, NEW_EVIDENCE, GAP_IDENTIFIED, GAP_CLOSED, PATTERN_DRIVEN_PROPOSAL, OPERATIONALIZATION_LINKED
- `EvolutionEvent` dataclass — id, capability_id, event_type, before_state, after_state, trigger_pattern_id, trigger_outcome_id, timestamp, description
- `CapabilityTrajectory` dataclass — capability_id, capability_name, current_maturity, maturity_trend, events, predicted_next_level, time_to_next_level_days
- `EvolutionSnapshot` dataclass — trajectories, advancing, declining, stalled, evolution_velocity

**Composes**:
- `CapabilityRuntime` — list_capabilities(), maturity_score(), evidence_for(), propose_from_patterns()
- `CapabilityPortfolioRuntime` — compounding_score(), health(), snapshot()
- `OutcomePatternEngine` (C12.1) — patterns_for_capability(), correlations()
- `LearningExtractionRuntime` (C12.0) — lessons_by_category(CAPABILITY_GAP)
- `CompoundingEngine` — detect_insight_to_capability(), detect_capability_to_operationalization()

**Public API**: trajectory(), all_trajectories(), advancing(), declining(), stalled(), evolution_recommendations(), snapshot(), summary(), health()

**Persistence**: JSONL at `data/umh/learning/evolution_events.jsonl`

**Logic**: Builds per-capability event timeline from evidence history + CompoundingEngine promotion candidates. Maturity trend via linear regression over maturity_score snapshots. Stalled = no new evidence and no maturity change within threshold. Recommendations: high pattern-correlation + low maturity = invest targets; declining + active goals = risk flags.

---

## C12.3 — LearningPortfolioRuntime

**File**: `substrate/organism/learning_portfolio_runtime.py` (~550 LOC)

**New types**:
- `LearningHealth(str, Enum)` — THRIVING, HEALTHY, STAGNANT, DECLINING, CRITICAL
- `LearningDriftType(str, Enum)` — LESSON_STALENESS, PATTERN_BLINDNESS, CAPABILITY_STALL, OUTCOME_LOOP_SILENCE, COMPOUNDING_BLOCKAGE
- `LearningDriftWarning` dataclass — drift_type, severity, description, affected_ids, recommendation
- `LearningPortfolioSnapshot` dataclass — lesson_count, pattern_count, active_trajectories, compounding_score, lesson_velocity, pattern_velocity, evolution_velocity, drift_warnings, health, top_lessons, top_patterns, top_trajectories

**Composes**:
- `LearningExtractionRuntime` (C12.0)
- `OutcomePatternEngine` (C12.1)
- `CapabilityEvolutionEngine` (C12.2)
- `OutcomeLearningLoop`
- `CompoundingEngine`
- `WorkPortfolioRuntime` (C11.2) — for cross-portfolio drift detection
- `CapabilityPortfolioRuntime` (C10.2)

**Public API**: snapshot(), health(), drift_warnings(), compounding_score(), lesson_velocity(), learning_effectiveness(), summary()

**No persistence** — pure read-only composition façade.

**Logic**: Health = f(lesson velocity, pattern freshness, evolution rate, compounding score). Drift: LESSON_STALENESS (no new lessons 7d), PATTERN_BLINDNESS (outcomes but no patterns), CAPABILITY_STALL (all stalled), OUTCOME_LOOP_SILENCE (no outcomes 3d), COMPOUNDING_BLOCKAGE (candidates but no promotions 14d).

---

## C12.4 — Executive Learning Cockpit

### Routes

**File**: `transports/api/cockpit_learning_routes.py` (~200 LOC)

**Endpoints** (all GET, prefix `/learning`):
```
/learning/overview           → LearningPortfolioSnapshot
/learning/lessons            → recent lessons
/learning/lessons/actionable → actionable lessons only
/learning/patterns           → top patterns
/learning/patterns/{id}      → single pattern detail
/learning/evolution          → all capability trajectories
/learning/evolution/{id}     → single trajectory
/learning/drift              → drift warnings
/learning/health             → health + effectiveness summary
/learning/compounding        → compounding report
```

### Frontend

**Store**: `cockpit/src/renderer/stores/learningStore.ts` (~150 LOC)
**Panel**: `cockpit/src/renderer/panels/LearningPanel.tsx` (~350 LOC) — 5 tabs: Overview, Lessons, Patterns, Evolution, Drift

### Integration Touches

- `cockpit/src/renderer/stores/cockpitStore.ts` — add `'learning'` to Panel type (also fix pre-existing `'workintelligence'` omission)
- `cockpit/src/renderer/components/Shell.tsx` — add `case 'learning': return <LearningPanel />`
- `transports/api/cockpit.py` — add `_mount_learning_router()`
- `substrate/organism/executive_brief_runtime.py` — add `_fill_learning()` method (~30 lines)
- `substrate/organism/strategic_context_runtime.py` — add `_fill_from_learning_system()` method (~30 lines)

---

## Implementation Order

```
C12.0 (LearningExtraction)       → composes only existing subsystems
C12.1 (OutcomePattern)            → depends on C12.0
C12.2 (CapabilityEvolution)       → depends on C12.0 + C12.1
C12.3 (LearningPortfolio)         → depends on C12.0 + C12.1 + C12.2
C12.4 (Cockpit + Integration)     → depends on all above
```

## Files Summary

**Created (11 new files):**
1. `substrate/organism/learning_extraction_runtime.py`
2. `substrate/organism/outcome_pattern_engine.py`
3. `substrate/organism/capability_evolution_engine.py`
4. `substrate/organism/learning_portfolio_runtime.py`
5. `transports/api/cockpit_learning_routes.py`
6. `cockpit/src/renderer/stores/learningStore.ts`
7. `cockpit/src/renderer/panels/LearningPanel.tsx`
8. `tests/test_learning_extraction_runtime.py`
9. `tests/test_outcome_pattern_engine.py`
10. `tests/test_capability_evolution_engine.py`
11. `tests/test_learning_portfolio_runtime.py`
12. `tests/test_learning_routes.py`

**Modified (6 existing files):**
1. `substrate/canonical_types.py` — ~15 new type registrations
2. `cockpit/src/renderer/stores/cockpitStore.ts` — add `'learning'` + fix `'workintelligence'`
3. `cockpit/src/renderer/components/Shell.tsx` — add `case 'learning':`
4. `transports/api/cockpit.py` — add `_mount_learning_router()`
5. `substrate/organism/executive_brief_runtime.py` — add `_fill_learning()`
6. `substrate/organism/strategic_context_runtime.py` — add `_fill_from_learning_system()`

## Invariants

- **Deterministic-first**: Zero LLM calls. All classification is rule-based.
- **Read-only**: C12 never mutates source subsystem state. OutcomeLearningLoop, DecisionRegistry, etc. remain authorities.
- **Composition via constructor injection**: Every dependency `Any | None = None`.
- **Error isolation**: Each `_fill_from_*` method wraps in try/except with `logger.debug()`.
- **Type coherence**: All new enums/dataclasses registered in `canonical_types.py`.
- **Python 3.11**: No 3.12+ syntax.

## Verification

Per-phase:
1. `python3 -m py_compile substrate/organism/<file>.py`
2. `pytest tests/test_<file>.py -v`
3. Import check: `python3 -c "from substrate.organism.<mod> import <Class>; print('ok')"`

Final:
1. Full test suite: `pytest tests/test_learning_*.py tests/test_outcome_pattern*.py tests/test_capability_evolution*.py -v`
2. `python3 scripts/check_type_divergence.py --all`
3. `python3 scripts/check_dependency_direction.py --all`
4. `python3 scripts/check_instance_leak.py --all`
5. TypeScript: `cd cockpit && npx tsc --noEmit`

## Estimated Scope

| Phase | LOC | Tests |
|-------|-----|-------|
| C12.0 LearningExtraction | ~500 | ~25 |
| C12.1 OutcomePattern | ~550 | ~30 |
| C12.2 CapabilityEvolution | ~450 | ~25 |
| C12.3 LearningPortfolio | ~550 | ~25 |
| C12.4 Cockpit + Integration | ~700 | ~15 |
| **Total** | **~2,750** | **~120** |

## Commit

```
feat(C12): add learning intelligence & outcome compounding — 4 runtimes, ~120 tests
```
