# Phase 50 — Outcome Memory + Execution Feedback Bridge v1

## Audit Report

**Date:** 2026-04-30
**Phase:** 50 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New files
- `umh/runtime/outcome.py` — OutcomeStatus, StrategyOutcome, DecisionOutcomeLink, StrategyStats, StrategyPerformanceSignal
- `umh/runtime/outcome_memory.py` — OutcomeMemory (append-only outcome storage with query and aggregation)
- `umh/runtime/feedback_bridge.py` — FeedbackBridge, FeedbackRecord (state → decision → outcome linkage with explanations)

### Modified files
- `umh/runtime/__init__.py` — 8 new exports, updated docstring

### Test file
- `tests/unit/test_phase50_outcome_feedback.py` — 161 tests across 42 sections

---

## Architecture

### Problem solved

Phases 30-49 gave UMH the ability to observe, classify, model, score, arbitrate, simulate, and track temporal dynamics. But UMH had no consequence memory — it couldn't answer "did strategy X work under state Y?" Phase 50 closes the first execution-learning loop by capturing outcomes and linking them to the state and decision that produced them.

### Three-module design

| Module | Responsibility |
|--------|---------------|
| `outcome.py` | Data models — frozen records of what happened |
| `outcome_memory.py` | Storage — append-only memory with query and aggregation |
| `feedback_bridge.py` | Orchestration — links state → decision → outcome, produces feedback |

### Outcome model

**StrategyOutcome** captures a single execution result:

| Field | Type | Bounds | Default |
|-------|------|--------|---------|
| outcome_id | str | — | required |
| decision_id | str | — | required |
| action_name | str | — | required |
| strategy_name | str | — | required |
| state_signature | str | — | required |
| status | OutcomeStatus | SUCCESS/FAILURE/PARTIAL/UNKNOWN | UNKNOWN |
| success_score | float | [0.0, 1.0] | 0.0 |
| latency | float | [0.0, ∞) | 0.0 |
| effort | float | [0.0, 1.0] | 0.0 |
| error_count | int | [0, ∞) | 0 |
| timestamp | str | auto-set | iso_now() |
| metadata | dict | — | {} |

All numeric fields are clamped in `__post_init__`. The dataclass is frozen — outcomes are immutable after creation.

### Decision-outcome linkage

**DecisionOutcomeLink** connects the chain:
```
state_signature → decision_id → strategy_name → objective_id → outcome_id
```

This enables queries like "under state X, when we chose strategy Y for objective Z, what happened?"

### Outcome memory

**OutcomeMemory** is append-only:
- `append(outcome)` — add an outcome
- `list_outcomes()` — returns a copy of all outcomes
- `query_by_strategy(name)` — filter by strategy
- `query_by_state(signature)` — filter by state
- `query_by_state_and_strategy(sig, name)` — combined filter
- `compute_strategy_stats(name)` — aggregate stats
- `compute_state_strategy_stats(sig, name)` — state-specific stats
- `get_performance_signal(name)` — stats with confidence
- `get_strategy_feedback_factor(name, state=None)` — planning hook

No `remove()`, `delete()`, `clear()`, or `pop()` methods exist. Historical outcomes are never mutated.

### Strategy statistics

**StrategyStats** aggregates:
- total_count, success_count, failure_count, partial_count, unknown_count
- average_success_score, average_latency, average_effort
- success_rate (computed property)

### Performance signal with confidence

**StrategyPerformanceSignal** adds:
```
confidence = min(1.0, sample_size / required_samples)
```
Default required_samples = 10. Consumers can check confidence before trusting the signal.

### Feedback factor

```
get_strategy_feedback_factor(strategy_name, state_signature=None):
    if total_count < required_samples: return 1.0  # neutral
    deviation = average_success_score - 0.5
    raw = 1.0 + deviation * 0.2
    return clamp(raw, 0.90, 1.10)
```

- Insufficient data → neutral (1.0)
- Strong positive history (score > 0.5) → boost up to 1.10
- Poor history (score < 0.5) → suppress down to 0.90
- Balanced history (score = 0.5) → neutral (1.0)

### Feedback bridge

**FeedbackBridge** orchestrates recording:
1. Appends outcome to OutcomeMemory
2. Creates a DecisionOutcomeLink
3. Computes strategy stats (global and state-specific)
4. Builds an explanation string
5. Returns a frozen FeedbackRecord

The bridge does NOT execute actions. It only records and summarizes.

### Explanation format

Every FeedbackRecord includes an explanation with:
- Strategy used and outcome status/score
- State signature
- Global execution history (count, success rate, avg score)
- State-specific execution history
- Confidence level (LOW with sample count, or "sufficient data")

### Pipeline position

```
scoring chain selects strategy
  → strategy executes (external)
  → StrategyOutcome created
  → FeedbackBridge.record_outcome()        [Phase 50 — NEW]
  → OutcomeMemory stores outcome           [Phase 50 — NEW]
  → DecisionOutcomeLink created            [Phase 50 — NEW]
  → FeedbackRecord returned                [Phase 50 — NEW]
  → get_strategy_feedback_factor() available for future planning
```

### Naming: StrategyOutcome vs ExecutionOutcome

Phase 50's `StrategyOutcome` is distinct from `calibration.py`'s existing `ExecutionOutcome`. The calibration outcome tracks simulation-vs-reality metrics (completion_rate, failure_rate). The strategy outcome tracks the learning loop (was strategy X effective under state Y?). Both can coexist — they serve different purposes in the pipeline.

---

## Tradeoffs

**Append-only, no persistence**: OutcomeMemory is in-memory and append-only. No disk persistence for v1. This means outcomes are lost on restart, but the design is correct for v1 — adding persistence later is a storage concern, not an architecture change.

**Factor clamped [0.90, 1.10]**: The feedback factor is conservative. Even with 100% success history, the maximum boost is 10%. This prevents the feedback loop from dominating the scoring chain before the data quality is proven.

**No automatic wiring**: The feedback factor is available via `get_strategy_feedback_factor()` but is NOT automatically multiplied into the scoring chain. Consumers must explicitly call it. This prevents accidental destabilization.

**Confidence threshold at required_samples**: Below the threshold, the factor is exactly 1.0 (neutral). There's no partial-confidence weighting — it's binary (insufficient = neutral, sufficient = use the data). This is intentionally simple for v1.

---

## Hard invariants

| ID  | Invariant                                              | Status |
|-----|--------------------------------------------------------|--------|
| 186 | Outcome memory must be append-only                     | PASS   |
| 187 | Historical outcomes must never be mutated              | PASS   |
| 188 | Feedback bridge must not directly execute actions      | PASS   |
| 189 | Outcome records must link state → decision → result    | PASS   |
| 190 | Missing outcome data must degrade gracefully           | PASS   |

---

## Test results

- **Phase 50 tests:** 161 passed, 0 failed
- **Phase 49 regression:** 161 passed, 0 failed
- **Phase 30-50 regression:** 3117 passed, 0 failed

---

## Dependency boundary

**outcome.py** imports only:
- `__future__.annotations`, `dataclasses`, `enum`, `typing`
- `umh.core.clock` (iso_now for timestamps)

**outcome_memory.py** imports only:
- `__future__.annotations`, `typing`
- `umh.runtime.outcome` (OutcomeStatus, StrategyOutcome, StrategyPerformanceSignal, StrategyStats)

**feedback_bridge.py** imports only:
- `__future__.annotations`, `dataclasses`, `typing`
- `umh.runtime.outcome` (DecisionOutcomeLink, StrategyOutcome, StrategyStats)
- `umh.runtime.outcome_memory` (OutcomeMemory)

No imports from `umh/cells`, `umh/environments`, `umh/adapters`, `subprocess`, or shell.

---

## Known limitations

- In-memory only — no durable persistence
- No automatic execution capture — outcomes must be explicitly created and passed to the bridge
- No learned strategy model — stats are descriptive, not predictive
- Feedback factor is optional and disabled by default in the scoring chain
- No time-weighted decay — all outcomes contribute equally regardless of age
- No cross-strategy comparison or ranking
- No automatic outlier detection in outcome history

---

## Files verified

```
py_compile: outcome.py ✓
py_compile: outcome_memory.py ✓
py_compile: feedback_bridge.py ✓
py_compile: __init__.py ✓
ruff format: all files ✓
```
