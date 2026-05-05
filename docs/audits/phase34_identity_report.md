# Phase 34: Identity Layer + Preference Formation v1 — Audit Report

**Date**: 2026-04-30
**Status**: COMPLETE
**Tests**: 102 passed, 0 failed
**Regression**: 1993 passed (phases 11-34), 0 regressions

---

## Deliverables

### New Modules (1)

| File | Purpose | Lines |
|------|---------|-------|
| `umh/runtime/identity.py` | TraitSnapshot, IdentityProfile, IdentityInfluence, BehaviorSignals, SignalExtractor, IdentityStore, IdentityScorer | ~412 |

### Modified Modules (3)

| File | Changes |
|------|---------|
| `umh/runtime/meta_planner.py` | SequenceEvaluator: added `identity_scorer` param, applies multiplicative identity factor in `score_sequence()`; MetaPlanner: added `identity_scorer` param with property; `_build_reason()` includes dominant identity trait |
| `umh/runtime/advisor.py` | Added `identity_store` constructor param, `_signal_extractor`, `_identity_goals_attempted/completed/switches` counters; `_update_identity()` method in tick; `identity_updated` tick key; identity in `get_state()`; identity reset in `clear()` |
| `umh/runtime/__init__.py` | Added 7 new exports (BehaviorSignals, IdentityInfluence, IdentityProfile, IdentityScorer, IdentityStore, SignalExtractor, TraitSnapshot) |

### Test File (1)

| File | Tests |
|------|-------|
| `tests/unit/test_phase34_identity.py` | 102 |

---

## Architecture

```
Runtime behavior (ticks, completions, switches)
        │
        ▼
SignalExtractor.extract()
        │
        ▼
BehaviorSignals {completion_rate, switch_frequency, success_rate, avg_seq_len}
        │
        ▼
IdentityStore.update_from_signals()
        │
        ▼  For each trait in TRAIT_SIGNAL_MAP:
        │    composite = Σ(weight_i × signal_i) / Σ(weight_i)
        │    trait_new = old + clamp(lr × (composite - old), ±max_delta)
        │    confidence += (1 - confidence) × 0.1
        │
        ▼
IdentityStore {traits, preferences, confidence, history}
        │
        ▼
IdentityScorer.compute_factor(seq_length, avg_effort, avg_priority)
        │
        ▼  Trait → bias mapping (multiplicative)
        │    factor = 1.0 + total_bias, clamped [0.80, 1.20]
        │
        ▼
SequenceEvaluator.score_sequence()
        │
        ▼  combined *= identity_factor (when scorer enabled)
```

---

## Identity Model

### Core Traits

| Trait | Signal Sources | Inversion | Meaning |
|-------|---------------|-----------|---------|
| persistence | completion_rate (0.5), switch_frequency (0.5, inv) | switch_freq inverted | Tendency to commit and finish |
| ambition | avg_sequence_length (0.6), success_rate (0.4) | — | Preference for complex long-horizon goals |
| risk_tolerance | switch_frequency (0.4), success_rate (0.6, inv) | success_rate inverted | Willingness to switch and explore |
| efficiency | completion_rate (0.7), success_rate (0.3) | — | Track record of completing effectively |

### Update Rule

```
raw_delta = learning_rate × (signal - old_value)
clamped_delta = clamp(raw_delta, -max_delta, +max_delta)
new_value = clamp(old + clamped_delta, 0.0, 1.0)
```

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| learning_rate | 0.08 | [0.01, 0.20] | Speed of trait adaptation |
| max_delta | 0.15 | [0.01, 0.50] | Maximum change per update |

### Confidence Model

```
new_confidence = min(1.0, old_confidence + (1.0 - old_confidence) × 0.1)
```

Confidence starts at 0.0 and approaches 1.0 asymptotically. It weights how much a trait contributes to the scoring factor.

---

## Scoring Integration

### Identity Factor Computation

```
For each trait with confidence > 0:
    bias = (trait_value - 0.5) × signal_strength × trait_weight × confidence

factor = clamp(1.0 + Σ bias, 0.80, 1.20)
```

| Trait | Signal | Weight | Effect |
|-------|--------|--------|--------|
| persistence | sequence_length / 4.0 | 0.20 | Boosts long sequences when persistent |
| ambition | avg_effort / 3.0 | 0.15 | Boosts high-effort goals when ambitious |
| efficiency | 1 - avg_effort / 5.0 | 0.15 | Boosts low-effort goals when efficient |
| risk_tolerance | avg_priority / 10.0 | 0.10 | Boosts high-priority goals when risk-tolerant |

### Key Property: Multiplicative, Not Overriding

The identity factor is always in **[0.80, 1.20]** — at most a ±20% nudge to the base score. Identity never overrides the meta-planner's fundamental ranking logic; it only biases it.

---

## Signal Extraction

| Signal | Source | Default |
|--------|--------|---------|
| completion_rate | goals_completed / goals_attempted | 0.5 |
| switch_frequency | switches / total_ticks | 0.0 |
| success_rate | goals_completed / goals_attempted | 0.5 |
| avg_sequence_length | total_sequence_steps / sequences_evaluated | 1.0 |

---

## Advisor Integration

### Tick Flow (Updated)

```
1-14. [existing stages]
15. Commit to goal
16. Track switches for identity
17. ★ Update identity (NEW)    ← extract signals, update traits
18. Persist state
```

---

## Hard Invariants

| ID | Invariant | Verified |
|----|-----------|----------|
| 106 | Identity updates must be append-only | YES — test_inv106_updates_append_only, test_inv106_no_history_deletion |
| 107 | Identity must NOT mutate execution state directly | YES — test_inv107_identity_no_execution_mutation (AST import analysis) |
| 108 | Identity influence must be multiplicative, not overriding | YES — test_inv108_multiplicative_not_overriding, test_inv108_extreme_low |
| 109 | Identity must update slowly (bounded delta) | YES — test_inv109_bounded_delta, test_inv109_bounded_delta_negative |
| 110 | Determinism preserved unless identity enabled | YES — test_inv110_determinism_without_identity, test_inv110_determinism_without_identity_none |

---

## Test Breakdown

| Section | Tests | Coverage |
|---------|-------|----------|
| TraitSnapshot | 3 | Creation, frozen, to_dict |
| IdentityProfile | 4 | Creation, frozen, to_dict sorted, empty |
| IdentityInfluence | 4 | Creation, frozen, to_dict, neutral |
| BehaviorSignals | 5 | Creation, defaults, clamped, frozen, to_dict |
| SignalExtractor | 4 | Default, with data, zero ticks, zero attempted |
| IdentityStore basics | 9 | Empty, default trait, confidence, preference (3), learning rate (3), max delta |
| IdentityStore update_trait | 9 | First update, EMA, bounded delta, convergence, clamped range, confidence growth (2), history, timestamp |
| IdentityStore signals | 5 | All mapped traits, high completion, high switching, bounded changes, neutral moderate |
| IdentityStore profile/clear | 4 | Profile, clear, to_dict, history copy |
| IdentityScorer | 12 | Disabled, no store, default neutral, high persistence boost, low persistence penalty, clamped min, clamped max, contributions, reason, properties, deterministic, fresh store neutral |
| Meta-planner integration | 7 | Evaluator property (2), score affected, disabled no effect, planner property (2), reason includes identity |
| Advisor integration | 9 | Store property (2), tick key, updates, get_state, clear, no store skips, evolves over ticks, switch tracking |
| Stability | 4 | Single extreme bounded, alternating stable, gradual drift, scorer stability |
| Hard invariants 106-110 | 9 | INV 106 (2), 107, 108 (2), 109 (2), 110 (2) |
| Boundary/exports | 14 | Imports (2), compile (4), all exports, e2e pipeline, e2e advisor, trait map, scorer neutral, influence to_dict, signals to_dict, ambition boost, efficiency boost |
| **Total** | **102** | |

---

## Decision Hierarchy (Complete)

```
IdentityScorer     → BIAS scoring by learned traits (Phase 34) ←── identity layer
CommitmentEngine   → PERSIST or SWITCH goal (Phase 33)
MetaPlanner        → which SEQUENCE of goals (Phase 31)
ArbitrationEngine  → which single GOAL (Phase 30)
TrajectoryPlanner  → which multi-step PATH (Phase 29)
StrategySimulator  → which STRATEGY variant (Phase 26)
ExecutionStrategy  → HOW to execute (Phase 25)
```

---

## Known Limitations

- No multi-user identity (single organism profile)
- No deep trait hierarchy (flat 4-trait model)
- No long-horizon reinforcement from outcome history
- No decay or forgetting (traits only drift, never reset)
- Trait-signal mapping is static (not learned)
- Scoring factor capped at ±20% (intentionally conservative)
- No cross-trait interaction modeling
- Preferences are set manually, not derived from behavior
- No goal-type classification for fine-grained bias

---

## Cumulative Test Count (Phases 11-34)

| Phase | Tests | Cumulative |
|-------|-------|------------|
| 11B-11F | 259 | 259 |
| 12 | 49 | 308 |
| 13 | 55 | 363 |
| 14 | 50 | 413 |
| 15 | 17 | 430 |
| 16 | 47 | 477 |
| 17 | 61 | 538 |
| 18 | 57 | 595 |
| 19 | 51 | 646 |
| 20 | 71 | 717 |
| 21 | 78 | 795 |
| 22 | 73 | 868 |
| 23 | 83 | 951 |
| 24 | 82 | 1033 |
| 25 | 88 | 1121 |
| 26 | 79 | 1200 |
| 27 | 80 | 1280 |
| 28 | 92 | 1372 |
| 29 | 94 | 1466 |
| 30 | 99 | 1565 |
| 31 | 97 | 1662 |
| 32 | 116 | 1778 |
| 33 | 113 | 1891 |
| **34** | **102** | **1993** |
