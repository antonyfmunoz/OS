# Phase 58 — Regime-Aware Strategy Orchestration v1

## Audit Report

**Date:** 2026-05-01
**Phase:** 58 of UMH runtime build
**Status:** COMPLETE

---

## What changed after Phase 57

Phase 57 introduced a controlled feedback selection layer — bounded, confidence-gated adjustments that can reorder candidates without destabilizing base scoring. But feedback selection operated in isolation: the caller had to manually compose regime weights and feedback factors. Phase 58 introduces a unified strategy orchestration pipeline that combines base scores, regime weights, and optional feedback selection into a single deterministic decision, with strict computation ordering and full explainability.

---

## What was built

### New files
- `umh/runtime/strategy_orchestrator.py` — StrategyOrchestrationPolicy, StrategyCandidate, StrategySelectionResult, orchestrate_selection

### Modified files
- `umh/runtime/__init__.py` — 4 new exports, updated docstring
- `umh/runtime/meta_planner.py` — optional orchestration_policy parameter, lazy orchestration integration in plan()

### Test file
- `tests/unit/test_phase58_strategy_orchestration.py` — 167 tests across 66 sections

### Also modified
- `tests/unit/test_phase57_feedback_selection.py` — Section 58 updated to verify orchestration integration (was previously asserting meta planner unchanged)

---

## Architecture

### Computation order (strict)

```
base_score → regime_factor → feedback_factor (opt-in)
```

Each layer is independently toggleable. Default: base + regime only (feedback disabled).

### Strategy orchestration policy

**StrategyOrchestrationPolicy** (frozen dataclass):

| Field | Default | Purpose |
|-------|---------|---------|
| use_regime_weighting | True | Apply regime factors to base scores |
| use_feedback_selection | False | Enable Phase 57 feedback selection |
| feedback_policy | None | Custom FeedbackSelectionPolicy |
| require_valid | True | Require at least one valid candidate |

### Strategy candidate

**StrategyCandidate** (frozen dataclass):

| Field | Default | Bounds |
|-------|---------|--------|
| strategy_id | "" | — |
| base_score | 0.0 | [0.0, 2.0] |
| regime_factor | 1.0 | [0.85, 1.15] |
| feedback_factor | 1.0 | [0.0, 2.0] |
| confidence | 0.0 | [0.0, 1.0] |
| valid | True | — |
| safe | True | — |

Computed properties:
- `regime_adjusted_score` = base_score × regime_factor
- `final_score` = base_score × regime_factor × feedback_factor

### Scoring pipeline

`orchestrate_selection(strategy_ids, base_scores, regime_factors, feedback_factors, confidences, valid_flags, safe_flags, policy)`:

1. **Validate** → empty list returns immediately
2. **Normalize** → pad/truncate all input lists to match strategy_ids length
3. **Effective validity** → combined: valid AND safe
4. **Base winner** → highest base_score among valid candidates
5. **Regime weighting** (if enabled) → base_score × clamped regime_factor [0.85, 1.15]
6. **Regime winner** → highest regime-adjusted score among valid candidates
7. **Feedback selection** (if enabled) → delegates to Phase 57's `select_with_feedback()` using regime_scores as input
8. **Final selection** → feedback winner if feedback enabled, else regime winner
9. **Build candidates** → StrategyCandidate per strategy with all layers
10. **Build explanation** → human-readable multi-stage explanation

### Regime factor bounds

```
_REGIME_FACTOR_MIN = 0.85
_REGIME_FACTOR_MAX = 1.15
```

Regime factors are clamped to this range — a ±15% maximum influence on base scores.

### Feedback integration

When `use_feedback_selection=True`, the orchestrator calls Phase 57's `select_with_feedback()` with regime-adjusted scores as the base. This means feedback operates on already-regime-weighted scores, preserving the strict computation order.

### Validity filtering

- `valid_flags`: invalid candidates excluded from selection
- `safe_flags`: unsafe candidates excluded from selection
- Combined: `effective_valid = valid AND safe`
- If all candidates invalid/unsafe and `require_valid=True`: empty result with explanation
- Missing flags default to True (legacy compatibility)

### Determinism / tie-breaking

- No randomness (no `import random`)
- Ties broken by strategy_id (lexicographic, ascending)
- Same inputs always produce same outputs

### Explainability

Every `StrategySelectionResult` includes:
- `selected_strategy`: final decision
- `base_winner`: who would have won on base scores alone
- `regime_winner`: who won after regime weighting
- `feedback_winner`: who won after feedback (if enabled)
- `changed_from_base`: whether regime/feedback changed outcome from base
- `changed_from_regime`: whether feedback changed outcome from regime
- `explanation`: human-readable multi-stage explanation string
- Per-candidate `StrategyCandidate` objects with all scoring layers

### Meta planner integration

`MetaPlanner` now accepts:
- `orchestration_policy` constructor parameter (default None)
- `plan()` accepts optional `regime_factors`, `feedback_factors`, `confidences` kwargs

When `orchestration_policy is not None` and ranking produces candidates:
1. Maps sequence labels to strategy IDs
2. Extracts base scores from ranked sequences
3. Calls `orchestrate_selection()` with all factors
4. Returns the matching ObjectiveSequence

Lazy import of `orchestrate_selection` inside `_orchestrated_select()` prevents circular dependencies.

When `orchestration_policy is None` (default): original plan() behavior is completely preserved.

---

## Hard invariants verified

| # | Invariant | Verified |
|---|-----------|----------|
| 233 | Pure computation, no scoring mutation | Sections 35, 36, 37, 61 |
| 234 | Regime factor bounded [0.85, 1.15] | Sections 14, 15, 17, 59 |
| 235 | Feedback integration opt-in, Phase 57 delegation | Sections 18, 19, 62, 65 |
| 236 | Default selection = base + regime only | Sections 12, 55 |
| 237 | Deterministic, no randomness | Sections 26, 27, 28 |
| 238 | Meta planner backward compatible | Sections 46, 47 |
| 239 | Full pipeline explainability | Sections 29, 30, 31, 32, 33, 57, 64 |
| 240 | Invalid/unsafe candidates never selected | Sections 23, 24, 25, 53, 66 |
| 241 | Missing inputs degrade to neutral | Sections 34, 40 |

---

## Test coverage

- **167 tests** across 66 sections
- Policy defaults/dict/frozen: Sections 1-3 (7 tests)
- Candidate defaults/bounds/computed/dict/frozen: Sections 4-8 (18 tests)
- Result defaults/dict/frozen: Sections 9-11 (7 tests)
- Default behavior: Section 12 (4 tests)
- Empty strategies: Section 13 (2 tests)
- Regime boost/penalty/neutral/bounded: Sections 14-17 (10 tests)
- Feedback disabled/enabled: Sections 18-19 (6 tests)
- Low-confidence feedback: Section 20 (2 tests)
- Composition: Section 21 (3 tests)
- Ordering: Section 22 (3 tests)
- Invalid/unsafe/all-invalid candidates: Sections 23-25 (6 tests)
- Determinism/tie-breaking/no randomness: Sections 26-28 (6 tests)
- Explainability (all stages): Sections 29-33 (9 tests)
- Missing inputs: Section 34 (4 tests)
- No scoring mutation: Section 35 (3 tests)
- Boundary compliance: Section 36 (4 tests)
- No execution: Section 37 (4 tests)
- Import surface: Section 38 (1 test)
- Regime disabled: Section 39 (3 tests)
- Length mismatches: Section 40 (4 tests)
- Single strategy: Section 41 (2 tests)
- Many strategies (100): Section 42 (2 tests)
- Stress test: Section 43 (2 tests)
- Feedback factor pass-through: Section 44 (2 tests)
- Base scores dominant: Section 45 (2 tests)
- Meta planner default/orchestration: Sections 46-47 (5 tests)
- Changed fields: Section 48 (3 tests)
- Candidate in result: Section 49 (2 tests)
- Explanation populated: Section 50 (2 tests)
- Full pipeline: Section 51 (3 tests)
- Zero base scores: Section 52 (2 tests)
- Mixed flags: Section 53 (2 tests)
- Custom feedback policy: Section 54 (2 tests)
- Both disabled: Section 55 (2 tests)
- Regime change + feedback revert: Section 56 (2 tests)
- Full pipeline explanation: Section 57 (2 tests)
- Roundtrips: Section 58 (3 tests)
- Regime bounds edge: Section 59 (2 tests)
- Three-way competition: Section 60 (3 tests)
- No scoring modification: Section 61 (2 tests)
- End-to-end Phase 57 integration: Section 62 (3 tests)
- require_valid=False: Section 63 (2 tests)
- Disabled explanation: Section 64 (2 tests)
- Default feedback policy: Section 65 (2 tests)
- Valid/safe interaction: Section 66 (3 tests)

---

## Boundary compliance

- No imports from `umh.cells`, `umh.environments`, `umh.adapters`
- No `import os`, `import subprocess`, `import random`, or `docker` references
- Pure computation module — no I/O
- No mutation of input lists or candidate data
- Strategy orchestrator imports only `feedback_selection` — no circular dependencies
- Meta planner uses TYPE_CHECKING import for orchestration policy type

---

## Regression

- Phase 50: 161 passed, 0 failed
- Phase 51-54: 198 passed, 0 failed
- Phase 55: 151 passed, 0 failed
- Phase 56: 179 passed, 0 failed
- Phase 57: 194 passed, 0 failed
- Phase 58: 167 passed, 0 failed
- Phase 50-58 combined: 1050 passed, 0 failed

---

## Known limitations

- Regime factor bounds are fixed [0.85, 1.15] — no adaptive regime sensitivity
- No cross-strategy regime comparison
- No adaptive computation order based on context
- No automatic policy tuning
- No regime confidence weighting (regime factors treated as certain)
- No multi-objective orchestration (single composite score)
- No sequence-level orchestration
- Meta planner integration is optional parameter threading only — no deep wiring
- No orchestration persistence or cross-session memory

---

## Is Phase 59 safe?

Yes. Phase 58:
- Added one new module (`strategy_orchestrator.py`) with minimal modifications to existing modules
- Meta planner changes are backward compatible (all new parameters default to None)
- Exports are purely additive (4 new symbols in `__init__.py`)
- All data structures are frozen dataclasses
- Default system behavior completely unchanged (feedback integration disabled by default)
- No dependency on any external library
- 1050 tests pass across Phases 50-58 with zero regressions

Phase 59 can safely build on strategy orchestration to introduce:
- Adaptive regime factor bounds based on confidence
- Multi-objective orchestration with Pareto-optimal candidate surfaces
- Cross-strategy regime comparison and normalization
- Orchestration persistence for cross-session strategy memory
- Contextual bandit integration with orchestration-informed priors
- Pipeline telemetry and diagnostics
