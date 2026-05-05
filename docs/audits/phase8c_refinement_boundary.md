# Phase 8C: Adaptive Strategy Refinement — Completion Report

**Date:** 2026-04-27
**Status:** Complete

---

## Agents Used

| Agent | Task | Output |
|-------|------|--------|
| 1 — Core | History, scoring, refiner modules | umh/strategy/history.py, scoring.py, refiner.py |
| 2 — Integration | GoalEngine, API, CLI modifications | umh/goals/goal_engine.py, umh/control/*.py |
| 3 — Frontend | Evolution panel, Evolve button | frontend/index.html, app.js |
| 4 — Tests | 4 test suites across refinement layer | tests/unit/test_phase8c_*.py |
| Main — Integrator | Compile, format, regression, report | This report |

---

## Architecture: Immutable Versioned Refinement

Phase 8C adds a controlled learning layer on top of Phase 8B's deterministic strategy decomposition. Strategies are IMMUTABLE — refinement creates new versions, never modifies existing ones. Adaptation is ADVISORY — proposals require explicit operator approval.

```
┌──────────────────────────────────────────────────────────────────┐
│                   REFINEMENT LAYER (Phase 8C)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          StrategyHistory (per goal_id)                      │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                │  │
│  │  │ Version 1│→ │ Version 2│→ │ Version 3│  (active)       │  │
│  │  │ is_active│  │ is_active│  │ is_active│                 │  │
│  │  │  =false  │  │  =false  │  │  =true   │                │  │
│  │  └──────────┘  └──────────┘  └──────────┘                │  │
│  │       ↓              ↓              ↓                      │  │
│  │  PerformanceMetrics per version:                           │  │
│  │  tasks_completed, tasks_failed, tasks_retried,            │  │
│  │  total_duration_sec, evaluations                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          Scoring (pure functions)                           │  │
│  │                                                            │  │
│  │  efficiency (40%) — completion rate, retry penalty         │  │
│  │  reliability (40%) — inverse failure rate                  │  │
│  │  complexity (20%) — step count + complexity weights        │  │
│  │  overall = weighted sum (0.0–1.0)                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          Refiner (deterministic detection)                 │  │
│  │                                                            │  │
│  │  Detects:                                                  │  │
│  │  1. high_failure_rate  (success < 70%)                    │  │
│  │  2. frequent_retries   (retry rate > 25%)                 │  │
│  │  3. bottleneck         (HIGH complexity + >2 tasks)       │  │
│  │  4. dead_step          (PENDING after 2x min evals)       │  │
│  │                                                            │  │
│  │  Remediation:                                              │  │
│  │  - Failed steps → add validation prerequisite              │  │
│  │  - Bottlenecks → split into prepare + execute              │  │
│  │  - Dead steps → remove                                     │  │
│  │  - Retries → split complex steps (suggested only)          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          RefinementProposal (ADVISORY)                     │  │
│  │                                                            │  │
│  │  issues_detected, suggested_changes, new_strategy,        │  │
│  │  current_score, expected_improvement, confidence,         │  │
│  │  recommended (bool)                                        │  │
│  │                                                            │  │
│  │  recommended = true only when:                             │  │
│  │    expected_improvement > 0.1 AND evaluations >= 6         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Flow

```
OLD (Phase 8B):  goal → strategy → ready_steps → tasks
NEW (Phase 8C):  goal → strategy → ready_steps → tasks
                                                    ↓
                              record_task_outcome() ←┘
                                     ↓
                            auto-check refinement (evaluations >= 3)
                                     ↓
                            RefinementProposal (if issues detected)
                                     ↓
                            operator reviews → applies or ignores
                                     ↓
                            new Strategy version (if applied)
```

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/strategy/history.py` | 180 | PerformanceMetrics, StrategyVersion, StrategyHistory, store functions |
| `umh/strategy/scoring.py` | 110 | StrategyScore, score_strategy(), compare_versions(), pure scoring functions |
| `umh/strategy/refiner.py` | 341 | RefinementIssue, RefinementProposal, refine_strategy(), proposal store |
| `tests/unit/test_phase8c_history.py` | 175 | History + metrics tests (22) |
| `tests/unit/test_phase8c_scoring.py` | 123 | Scoring + comparison tests (12) |
| `tests/unit/test_phase8c_refinement.py` | 210 | Refinement + proposal tests (16) |
| `tests/unit/test_phase8c_integration.py` | 193 | AST boundary + engine integration tests (12) |

## Files Modified

| File | Change | Impact |
|------|--------|--------|
| `umh/goals/goal_engine.py` | +record_strategy_version, +record_task_outcome, +auto-refinement check, +refinement fields in result | Core — outcome tracking wired into task success/failure paths |
| `umh/control/api.py` | +refine endpoint, +apply_refinement endpoint, +history/proposal in GET goal | Additive |
| `umh/control/cli.py` | +goal-refine command, +goal-apply-refinement command | Additive |
| `frontend/index.html` | +Strategy Evolution panel with versions and proposal display | Additive |
| `frontend/app.js` | +Evolve button, +showEvolution, +triggerRefinement, +applyRefinement | Additive |

---

## Data Models

### PerformanceMetrics

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tasks_completed` | `int` | `0` | Successfully completed tasks |
| `tasks_failed` | `int` | `0` | Failed tasks |
| `tasks_retried` | `int` | `0` | Retried tasks |
| `total_duration_sec` | `float` | `0.0` | Cumulative duration |
| `evaluations` | `int` | `0` | Total evaluation count |
| **Properties** | | | |
| `success_rate` | `float` | computed | completed / (completed + failed) |
| `avg_duration_sec` | `float` | computed | total_duration / completed |

### StrategyVersion

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy` | `Strategy` | required | The strategy snapshot |
| `version` | `int` | `1` | Sequential version number |
| `version_id` | `str` | `sv_` + uuid | Unique version identifier |
| `created_at` | `str` | computed | ISO-8601 timestamp |
| `performance` | `PerformanceMetrics` | empty | Mutable performance data |
| `is_active` | `bool` | `True` | Only one active per history |
| `replaced_by` | `str` | `""` | Version ID of replacement |

### StrategyHistory

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `goal_id` | `str` | required | Parent goal reference |
| `versions` | `list[StrategyVersion]` | `[]` | All versions (append-only) |

Methods: `add_version()`, `active_version()`, `get_version()`, `latest_version()`, `version_count()`

### StrategyScore

| Field | Type | Range | Weight |
|-------|------|-------|--------|
| `efficiency` | `float` | 0.0–1.0 | 40% |
| `reliability` | `float` | 0.0–1.0 | 40% |
| `complexity` | `float` | 0.0–1.0 | 20% |
| `overall` | `float` | 0.0–1.0 | weighted sum |

### RefinementIssue

| Field | Type | Description |
|-------|------|-------------|
| `issue_type` | `str` | high_failure_rate, frequent_retries, bottleneck, dead_step |
| `description` | `str` | Human-readable issue description |
| `step_id` | `str` | Affected step (if applicable) |
| `severity` | `str` | high, medium, low |

### RefinementProposal

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | `ref_` + uuid |
| `goal_id` | `str` | Parent goal |
| `issues_detected` | `list[RefinementIssue]` | All detected issues |
| `suggested_changes` | `list[str]` | Human-readable change descriptions |
| `new_strategy` | `Strategy | None` | Candidate replacement strategy |
| `current_score` | `StrategyScore | None` | Score of current strategy |
| `expected_improvement` | `float` | Estimated score improvement |
| `confidence` | `float` | Confidence in proposal (0.0–1.0) |
| `recommended` | `bool` | True if improvement > 0.1 AND evaluations >= 6 |

---

## Scoring System

```
efficiency = success_rate - (retry_penalty * 0.2)
  where retry_penalty = min(retries / evaluations, 1.0)
  zero evaluations → 0.5 (neutral)

reliability = 1.0 - failure_rate
  where failure_rate = failed / (completed + failed)
  zero evaluations → 0.5 (neutral)

complexity = avg_complexity_weight - step_penalty
  where weights: LOW=1.0, MEDIUM=0.7, HIGH=0.4
  step_penalty = max(0, steps - 3) * 0.05
  no steps → 0.5 (neutral)

overall = efficiency * 0.4 + reliability * 0.4 + complexity * 0.2
```

---

## Detection Thresholds

| Detector | Threshold | Severity | Remediation |
|----------|-----------|----------|-------------|
| high_failure_rate | success_rate < 0.7 | high | Add validation prerequisite before failed steps |
| frequent_retries | retry_rate > 0.25 | medium | Split complex steps (suggested) |
| bottleneck | HIGH complexity + >2 tasks, not completed | medium | Split into prepare + execute |
| dead_step | PENDING after 2x min evaluations (6) | low | Remove from strategy |

---

## API Surface

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/goals/{id}/refine` | POST | Trigger refinement analysis |
| `/goals/{id}/apply_refinement` | POST | Apply stored proposal (invalidate old strategy, cache new, record version, clear proposal) |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /goals/{id}` | Now includes `strategy_history` and `refinement_proposal` |
| `GET /metrics` | Added `refinements.proposals_pending` count |

---

## CLI Commands

### New Commands

| Command | Description |
|---------|-------------|
| `goal-refine ID [--json]` | Show/compute refinement proposal |
| `goal-apply-refinement ID [--json]` | Apply stored refinement proposal |

---

## Events

| Event | Payload |
|-------|---------|
| `strategy.refinement_proposed` | goal_id, proposal_id, issues, expected_improvement, recommended |
| `strategy.refinement_applied` | goal_id, strategy_id (new), proposal_id, version |

---

## Boundary Verification

### Hard Constraint Proof

| # | Constraint | Status |
|---|-----------|--------|
| 1 | Strategies are IMMUTABLE — refinement creates new versions | PASS — refiner creates fresh Strategy via _build_refined_strategy() |
| 2 | Refinement is ADVISORY — never auto-applies | PASS — proposals stored, require explicit apply_refinement call |
| 3 | No execution imports in strategy layer | PASS — AST verified |
| 4 | No adapter imports in strategy layer | PASS — AST verified |
| 5 | No tool imports in strategy layer | PASS — AST verified |
| 6 | No execute() calls in strategy layer | PASS — AST verified |
| 7 | No Goal() creation in refiner | PASS — AST verified |
| 8 | No GoalEngine import in strategy layer | PASS — AST verified |
| 9 | Scoring is pure (no side effects) | PASS — functions take data, return data |
| 10 | All task objectives still route through planner→reviewer→validator→execution | PASS — GoalEngine.evaluate_goal() unchanged |

### Import Graph

```
umh/strategy/history.py    → umh.core.clock, umh.strategy.models
umh/strategy/scoring.py    → umh.strategy.history, umh.strategy.models
umh/strategy/refiner.py    → umh.core.clock, umh.events.stream
                           → umh.strategy.history, umh.strategy.models, umh.strategy.scoring
```

No imports from `umh.execution.engine`, `umh.adapters`, `umh.tools`, or `umh.goals.goal_engine`.

---

## Tests

### Phase 8C Tests

| Suite | Tests | Status |
|-------|-------|--------|
| test_phase8c_history.py | 22 | Pass |
| test_phase8c_scoring.py | 12 | Pass |
| test_phase8c_refinement.py | 16 | Pass |
| test_phase8c_integration.py | 12 | Pass |
| **Total Phase 8C** | **62** | **All pass** |

### Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 8B (strategy) | 84 | Pass |
| Phase 8A (goals) | 72 | Pass |
| Phase 7D (scheduler) | 71 | Pass |
| Phase 7C (agents) | 78 | Pass |
| Phase 7B (tools) | 114 | Pass |
| Phase 7A (memory) | 91 | Pass |
| Phase 6D+6E (async/retry/worker) | 142 | Pass |
| Phase 5A+6A+6B (spine, meta, control) | 153 | Pass |
| **Total verified** | **867+** | **All pass** |

### Validation

| Check | Result |
|-------|--------|
| `python3 -m py_compile` all Phase 8C files | All OK |
| `ruff format` all Phase 8C files | All formatted |
| No execute() calls in strategy/ | PASS (AST) |
| No adapter imports in strategy/ | PASS (AST) |
| No tool imports in strategy/ | PASS (AST) |
| No Goal() instantiation in refiner | PASS (AST) |
| No GoalEngine import in strategy/ | PASS (AST) |
| Strategy imports work | OK |

---

## Known Limitations

1. **In-memory history store** — version history lost on restart
2. **No automatic strategy application** — proposals require manual apply (by design)
3. **Step-level duration not tracked** — total_duration_sec is per-version, not per-step
4. **No A/B comparison runtime** — can compare scores but not run two strategies simultaneously
5. **Refinement detection is threshold-based** — no ML or trend analysis
6. **Proposal overwrite** — new refinement replaces existing unapplied proposal
7. **No rollback mechanism** — can't revert to a previous version (must recompute)
8. **Scoring assumes equal task weight** — no task-level importance weighting

---

## Success Condition Verification

> "Track performance per strategy version"

**VERIFIED.** PerformanceMetrics tracks tasks_completed, tasks_failed, tasks_retried, total_duration_sec, evaluations per version. record_task_outcome() updates the active version on every task completion/failure.

> "Score strategies deterministically"

**VERIFIED.** score_strategy() is a pure function: same PerformanceMetrics + Strategy → same StrategyScore. Three dimensions (efficiency 40%, reliability 40%, complexity 20%) combine into an overall score.

> "Detect performance issues"

**VERIFIED.** Four detection patterns with configurable thresholds: high_failure_rate (>30% failure), frequent_retries (>25% retry rate), bottleneck (HIGH complexity + >2 tasks), dead_step (PENDING after 2x min evaluations).

> "Propose refinements WITHOUT auto-applying"

**VERIFIED.** refine_strategy() returns a RefinementProposal that is stored but never applied. Application requires explicit POST /goals/{id}/apply_refinement or goal-apply-refinement CLI command.

> "Strategies are IMMUTABLE"

**VERIFIED.** _build_refined_strategy() creates a fresh Strategy object. Original strategy is never modified. New version is appended to StrategyHistory.

> "Preserve all invariants"

**VERIFIED.** Goal-generated tasks still route through planner→reviewer→validator→execution→guard. Approvals still required. No bypass. All Phase 8B invariants preserved.

> "NO recursion"

**VERIFIED.** AST inspection: no Goal() creation, no GoalEngine import in strategy layer. Refiner creates Strategy objects, not Goals.

> "NO auto-execution of proposals"

**VERIFIED.** RefinementProposal has `recommended` flag but never executes. Operator must call apply_refinement explicitly.
