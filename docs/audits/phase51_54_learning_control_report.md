# Phases 51-54 — Learning Control Block

## Audit Report

**Date:** 2026-04-30
**Phases:** 51-54 of UMH runtime build
**Status:** COMPLETE

---

## What was built

### New files
- `umh/runtime/outcome_persistence.py` — JSONL append-only file backend (FileOutcomePersistenceBackend, PersistenceResult)
- `umh/runtime/outcome_decay.py` — Temporal decay with exponential weighting (DecayConfig, DecayResult, compute_decay_weight, compute_decayed_stats)
- `umh/runtime/feedback_policy.py` — Controlled, bounded feedback influence (FeedbackPolicy, FeedbackInfluenceResult, compute_feedback_factor)
- `umh/runtime/learning_strength.py` — Adaptive dampening of feedback (LearningStrengthConfig, LearningStrengthResult, compute_learning_strength)
- `umh/runtime/exploration.py` — Bounded candidate selection policy (ExplorationPolicy, ExplorationDecision, SelectionMode, select_candidate)

### Modified files
- `umh/runtime/outcome_memory.py` — Added persistence_backend parameter, _load_from_backend(), persistence error tracking
- `umh/runtime/__init__.py` — 16 new exports, updated docstring

### Test file
- `tests/unit/test_phase51_54_learning_control.py` — 198 tests across 63 sections

---

## Architecture

### Problem solved

Phase 50 gave UMH an outcome memory and feedback bridge — it could record what happened. But it couldn't persist outcomes across restarts, weight recent results over old ones, control how strongly feedback influences scoring, adapt influence based on data quality, or explore alternatives when confidence is low. Phases 51-54 close these gaps as a single coherent learning-control block.

### Five-module design

| Module | Phase | Responsibility |
|--------|-------|---------------|
| `outcome_persistence.py` | 51 | Durable JSONL storage with atomic writes |
| `outcome_decay.py` | 51 | Time-weighted statistics via exponential decay |
| `feedback_policy.py` | 52 | Bounded, opt-in feedback influence |
| `learning_strength.py` | 53 | Adaptive dampening based on data quality |
| `exploration.py` | 54 | Bounded explore/exploit candidate selection |

### Data flow

```
Outcomes → Persist (JSONL)
         → Decay (time-weight)
         → Learning Strength (volatility + sample size → dampener)
         → Feedback Policy (bounded factor × learning strength)
         → Exploration (exploit best or explore alternative)
```

---

## Phase 51 — Persistence + Decay

### Persistence backend

- **Protocol**: `OutcomePersistenceBackend` with `append_outcome()` and `load_outcomes()`
- **File backend**: Atomic writes via `os.open(O_WRONLY | O_CREAT | O_APPEND, 0o644)`
- **Format**: JSONL (one JSON object per line, newline-delimited)
- **Corruption tolerance**: Invalid lines are skipped during load
- **No deletion**: No `delete()`, `remove()`, `clear()`, or `pop()` methods exist
- **OutcomeMemory integration**: Optional `persistence_backend` parameter; errors tracked but non-fatal

### Temporal decay

| Parameter | Default | Bounds |
|-----------|---------|--------|
| half_life_seconds | 86400 (1 day) | ≥ 1.0 |
| min_weight | 0.01 | [0.0, 1.0] |
| max_weight | 1.0 | [min_weight, 1.0] |

Formula: `weight = 0.5 ^ (age_seconds / half_life_seconds)`, clamped to `[min_weight, max_weight]`.

Produces `DecayResult` with weighted averages for score, latency, effort, and success rate.

---

## Phase 52 — Feedback Policy

### Policy controls

| Field | Default | Bounds |
|-------|---------|--------|
| enabled | False | — |
| min_effective_samples | 10 | ≥ 1 |
| max_boost | 0.10 | [0.0, 0.25] |
| max_penalty | 0.10 | [0.0, 0.25] |
| neutral_factor | 1.0 | — |

### Factor computation

```
deviation = avg_score - 0.5
raw_delta = clamp(deviation × 0.2, -max_penalty, max_boost)
effective_delta = raw_delta × learning_strength
factor = neutral + effective_delta, clamped to [neutral - max_penalty, neutral + max_boost]
```

### Safety guarantees
- Disabled by default → returns 1.0
- Insufficient samples → returns 1.0
- Factor always within [0.90, 1.10] with default config
- Explanation string always populated with direction, avg_score, samples, learning_strength, confidence

---

## Phase 53 — Learning Strength

### Adaptive dampening

| Parameter | Default | Bounds |
|-----------|---------|--------|
| min_strength | 0.25 | [0.0, 1.0] |
| max_strength | 1.0 | [min_strength, 1.0] |
| required_samples | 20 | ≥ 1 |
| volatility_penalty | 0.5 | [0.0, 1.0] |

### Computation

```
volatility = stddev(success_scores)
sample_factor = min(1.0, n / required_samples)
vol_reduction = volatility × volatility_penalty
raw = sample_factor × (1.0 - vol_reduction)
strength = clamp(raw, min_strength, max_strength)
```

### Interaction with feedback
`compute_feedback_factor()` accepts `learning_strength` parameter. The effective delta is:
```
effective_delta = raw_delta × learning_strength
```
This means volatile or sparse outcome data automatically reduces feedback influence without manual tuning.

---

## Phase 54 — Exploration

### Policy controls

| Field | Default | Bounds |
|-------|---------|--------|
| enabled | False | — |
| exploration_rate | 0.05 | [0.0, 0.25] |
| min_confidence_for_exploitation | 0.7 | [0.0, 1.0] |
| seed | None | — |

### Selection logic

1. No candidates → index -1, exploit mode
2. Disabled → exploit best score
3. High confidence (≥ threshold) → exploit best
4. Single candidate → exploit (can't explore)
5. Low confidence + enabled + multiple → explore:
   - With seed: deterministic selection via `seed % (n-1)` from non-best candidates
   - Without seed: select second-best by score

---

## Hard invariants verified

| # | Invariant | Verified |
|---|-----------|----------|
| 191 | Append-only persistence — no delete/remove/clear on backend | Sections 5, 38 |
| 192 | Historical immutability — loaded outcomes are frozen | Section 38 |
| 193 | No direct execution — all modules are pure computation or I/O-only | Sections 37, 55 |
| 194 | State → decision → result linkage preserved through persistence | Sections 4, 63 |
| 195 | Graceful degradation — persistence failure doesn't crash memory | Sections 4, 58 |
| 196 | Positive history boosts scoring factor | Section 12 |
| 197 | Bounded feedback — factor always within [0.90, 1.10] | Section 14 |
| 198 | Disabled by default — all new systems return neutral | Sections 10, 39 |
| 199 | Insufficient samples return neutral | Section 11 |
| 200 | Explanation string always populated | Section 15 |
| 201 | Deterministic — same inputs → same outputs | Sections 22, 30 |
| 202 | Strength bounded [min, max] | Section 21 |
| 203 | Sparse data reduces strength | Section 18 |
| 204 | Volatility reduces strength | Section 19 |
| 205 | Stable patterns increase strength | Section 20 |
| 206 | Exploration disabled → always exploits | Section 27 |
| 207 | High confidence → exploits | Section 28 |
| 208 | Exploration never selects invalid candidate | Section 41 |
| 209 | Exploration rate bounded [0.0, 0.25] | Section 31 |
| 210 | Seeded selection is deterministic | Section 30 |

---

## Test coverage

- **198 tests** across 63 sections
- Phase 51 (persistence): Sections 1-5, 44-45, 57-58 (49 tests)
- Phase 51 (decay): Sections 6-8, 40, 46-48, 59 (30 tests)
- Phase 52 (feedback policy): Sections 9-16, 49-50, 62 (30 tests)
- Phase 53 (learning strength): Sections 17-24, 51-52, 56, 60 (27 tests)
- Phase 54 (exploration): Sections 25-34, 53-54, 61 (32 tests)
- Cross-phase integration: Sections 35-43, 55, 63 (30 tests)

---

## Boundary compliance

All five modules verified clean:
- No imports from `umh.cells`, `umh.environments`, `umh.adapters`
- Pure computation modules (decay, policy, strength, exploration) have no `import os` or `import subprocess`
- Persistence module uses `os` only for file operations

---

## Regression

- Phase 50 re-verified: 161 passed (outcome_memory.py was modified)
- Full Phase 30-54 regression: all tests passed, zero failures
