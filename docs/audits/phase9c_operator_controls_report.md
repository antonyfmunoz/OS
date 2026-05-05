# Phase 9C: Operator Control + Intent Shaping Layer — Completion Report

**Date:** 2026-04-28
**Status:** Complete

---

## Agents Used

| Agent | Task | Output |
|-------|------|--------|
| 1 — Core | Controls model, scorer integration | umh/attention/controls.py, umh/attention/scorer.py |
| 2 — Integration | Worker, API, CLI modifications | umh/orchestrator/worker.py, umh/control/*.py |
| 3 — Frontend | System Controls panel | frontend/index.html, app.js |
| 4 — Tests | 2 test suites across controls layer | tests/unit/test_phase9c_*.py |
| Main — Integrator | Import fix, compile, format, regression, report | This report |

---

## Architecture: Behavior Modifiers, Not Execution Logic

Phase 9C introduces global controls that influence HOW the system behaves without changing WHAT it executes. Controls are pure configuration that modify scoring weights and thresholds — they never touch execution logic directly.

```
┌──────────────────────────────────────────────────────────────────┐
│                   OPERATOR CONTROLS (Phase 9C)                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          SystemControls (singleton)                        │  │
│  │                                                            │  │
│  │  execution_mode:     balanced | aggressive | conservative  │  │
│  │  max_concurrent_tasks: int (1-20)                         │  │
│  │  retry_policy:       strict (1) | normal (3) | lenient (5)│  │
│  │  cost_sensitivity:   0.0–1.0 (cost penalty multiplier)    │  │
│  │  failure_tolerance:  0.0–1.0 (failure dampening)          │  │
│  │  exploration_factor: 0.0–1.0 (strategy bias)              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                ┌─────────┼─────────┐                            │
│                ▼         ▼         ▼                            │
│         ┌──────────┐ ┌───────┐ ┌──────────┐                   │
│         │ Priority │ │Worker │ │Refinement│                    │
│         │ Scoring  │ │Limits │ │ Bias     │                    │
│         │(weights) │ │(max)  │ │(simple/  │                    │
│         │          │ │       │ │ complex) │                    │
│         └──────────┘ └───────┘ └──────────┘                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │          ControlInfluence (explainability)                 │  │
│  │                                                            │  │
│  │  mode, priority_adjustment, retry_policy,                 │  │
│  │  cost_modifier, failure_modifier                          │  │
│  │                                                            │  │
│  │  Attached to every priority scoring result.                │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Mode Effects

| Mode | Importance | Recency | Failure | Dependency | Cost |
|------|-----------|---------|---------|------------|------|
| Balanced | ×1.0 | ×1.0 | ×1.0 | ×1.0 | ×1.0 |
| Aggressive | ×1.3 | ×1.2 | ×0.7 | ×1.2 | ×0.5 |
| Conservative | ×0.8 | ×0.8 | ×1.4 | ×0.9 | ×1.5 |

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/attention/controls.py` | 218 | SystemControls, ExecutionMode, RetryPolicy, ControlInfluence, weight modifiers, singleton store |
| `tests/unit/test_phase9c_controls.py` | 286 | Controls model + scoring integration tests (25) |
| `tests/unit/test_phase9c_integration.py` | 238 | Boundary + determinism + mode transition tests (16) |

## Files Modified

| File | Lines | Change | Impact |
|------|-------|--------|--------|
| `umh/attention/scorer.py` | 233 | +score_task_with_controls() wrapping score_task | Core — control-aware scoring |
| `umh/orchestrator/worker.py` | 273 | Uses score_task_with_controls, respects max_concurrent_tasks | Core — worker throttled by controls |
| `umh/control/api.py` | 1947 | +GET/POST /system/controls, +control_influence in priority endpoint, +controls in metrics | Additive |
| `umh/control/cli.py` | 1744 | +controls command, +controls-set command | Additive |
| `frontend/index.html` | ~600 | +Controls nav button, +System Controls panel with sliders | Additive |
| `frontend/app.js` | ~1850 | +loadControls, +renderControls, +saveControls, +setMode | Additive |

---

## Control Model

### SystemControls

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `execution_mode` | ExecutionMode | BALANCED | Weight modifiers on all scoring dimensions |
| `max_concurrent_tasks` | int | 5 | Worker stops dequeuing at this limit |
| `retry_policy` | RetryPolicy | NORMAL | Maps to max retries: STRICT=1, NORMAL=3, LENIENT=5 |
| `cost_sensitivity` | float | 0.5 | 0–1, higher = bigger cost penalty in scoring |
| `failure_tolerance` | float | 0.5 | 0–1, higher = less failure pressure in scoring |
| `exploration_factor` | float | 0.3 | 0–1, strategy refinement bias (simple↔complex) |

### Scoring Integration

`score_task_with_controls()` wraps `score_task()`:
1. Computes base score via existing scorer
2. Applies multiplicative weight modifiers from execution mode
3. Applies additive cost_sensitivity adjustment
4. Applies failure_tolerance dampening for values > 0.5
5. Returns (PriorityEntry, ControlInfluence) tuple

---

## API Surface

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/system/controls` | GET | Return current system controls |
| `/system/controls` | POST | Update controls (partial or full), emits system.controls_updated event |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /tasks/{id}/priority` | Now includes `control_influence` in response |
| `GET /metrics` | Added `controls` section with mode, retry_policy, max_concurrent_tasks |

---

## CLI Commands

### New Commands

| Command | Description |
|---------|-------------|
| `controls [--json]` | Show current system controls |
| `controls-set <key> <value> [--json]` | Update a single control field |

---

## Events

| Event | Payload |
|-------|---------|
| `system.controls_updated` | controls dict, errors list |

---

## Integration Fix

**Issue:** Agent 2 imported `score_task_with_controls` from `umh.attention.controls` instead of `umh.attention.scorer` in the worker's `_poll_once` method.

**Fix:** Changed import to `from umh.attention.scorer import score_task_with_controls` in worker.py line 121.

**Root cause:** Two agents created code in parallel. Agent 1 placed `score_task_with_controls` in `scorer.py` (correct — keeps scoring functions together). Agent 2 assumed it was in `controls.py`. Single-line import fix.

---

## Boundary Verification

### Hard Constraint Proof

| # | Constraint | Status |
|---|-----------|--------|
| 1 | Controls are PURE CONFIGURATION (no execution) | PASS — AST verified |
| 2 | No execution imports in attention/ | PASS — AST verified |
| 3 | No adapter imports in attention/ | PASS — AST verified |
| 4 | No tool imports in attention/ | PASS — AST verified |
| 5 | No planning imports in attention/ | PASS — AST verified |
| 6 | No execute() calls in attention/ | PASS — AST verified |
| 7 | No GoalEngine import in attention/ | PASS — AST verified |
| 8 | Controls influence scoring deterministically | PASS — same controls + same task → same score |
| 9 | Controls do not mutate tasks or goals | PASS — task object unchanged after scoring |
| 10 | Mode effects are immediate | PASS — change mode, next score reflects it |

### Import Graph

```
umh/attention/controls.py  → umh.core.clock (only)
umh/attention/scorer.py    → umh.attention.priority, umh.attention.controls (lazy)
                           → umh.goals.models, umh.orchestrator.task
```

No imports from `umh.execution`, `umh.adapters`, `umh.tools`, `umh.planning`, or `umh.goals.goal_engine`.

---

## Tests

### Phase 9C Tests

| Suite | Tests | Status |
|-------|-------|--------|
| test_phase9c_controls.py | 25 | Pass |
| test_phase9c_integration.py | 16 | Pass |
| **Total Phase 9C** | **41** | **All pass** |

### Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 9A (attention queue) | 60 | Pass |
| Phase 8C (refinement) | 62 | Pass |
| Phase 8B (strategy) | 84 | Pass |
| Phase 8A (goals) | 72 | Pass |
| Phase 7D (scheduler) | 71 | Pass (background) |
| Phase 7C (agents) | 78 | Pass (background) |
| Phase 7B (tools) | 114 | Pass (background) |
| Phase 7A (memory) | 91 | Pass (background) |
| Phase 6D+6E (async/retry/worker) | 142 | Pass (background) |
| Phase 5A+6A+6B (spine, meta, control) | 153 | Pass (background) |
| **Total verified** | **968+** | **All pass** |

---

## Known Limitations

1. **In-memory controls store** — controls reset on restart
2. **No per-goal control overrides** — controls are global only
3. **No control history/audit log** — only current state tracked
4. **Exploration factor read but not wired** — refinement bias function exists but strategy layer doesn't read it yet
5. **No control validation constraints** — operator can set conflicting values (e.g., aggressive mode with strict retry)
6. **No gradual transition** — mode changes are instant, no ramp-up period
7. **Cost sensitivity is additive** — doesn't compound with mode-based cost modifier

---

## Success Condition Verification

> "Tune system behavior globally"

**VERIFIED.** SystemControls provides 6 tunable dimensions. Execution mode provides preset profiles. Individual sliders allow fine-grained control.

> "Adapt to different scenarios"

**VERIFIED.** Aggressive mode for high-throughput situations (boost importance, relax cost). Conservative mode for stability (increase failure pressure, reduce risk). Balanced for normal operation.

> "Maintain predictability"

**VERIFIED.** All scoring is deterministic. Same controls + same task state → same score. Mode transitions are immediate and testable. ControlInfluence provides full explainability.

> "Controls only influence scoring + decisions"

**VERIFIED.** Controls produce weight modifiers consumed by the scorer. They never touch execution, planning, or task mutation. AST boundary verification confirms no forbidden imports.

> "NO autonomy"

**VERIFIED.** Controls are operator-set only. No auto-adjustment, no learning, no adaptation without explicit operator action.

> "NO hidden decisions"

**VERIFIED.** Every scoring result includes ControlInfluence showing mode, priority_adjustment, retry_policy, cost_modifier, and failure_modifier. API, CLI, and UI all expose this.
