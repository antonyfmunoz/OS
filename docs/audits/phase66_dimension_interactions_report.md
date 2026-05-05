# Phase 66 — Cross-Dimension Interaction Layer v1

## Status: COMPLETE

## Summary

Phase 66 adds bounded pairwise interaction factors between regime dimensions.
Linear aggregation misses non-linear effects: high trend + high risk is worse
than either alone; low stability + high urgency compounds danger. The interaction
layer captures these effects with sparse, bounded, explainable modulation.

The core constraint: interaction_factor is clamped to [0.9, 1.1] — it can nudge
but never dominate. Maximum 3 active pairs prevent combinatorial explosion.

## Files

| File | Lines | Action | Purpose |
|------|-------|--------|---------|
| `umh/runtime/dimension_interactions.py` | 333 | NEW | InteractionConfig, InteractionRule, ActiveInteraction, InteractionResult, compute_interaction_factor |
| `umh/runtime/strategy_orchestrator.py` | 576 | MODIFIED | Added interaction_factor to StrategyCandidate, Step 5 interaction stage, InteractionConfig param, interaction_winner tracking |
| `umh/runtime/__init__.py` | 675 | MODIFIED | 7 new exports |
| `tests/unit/test_phase58_strategy_orchestration.py` | — | MODIFIED | Updated to_dict key sets, dependency whitelist |
| `tests/unit/test_phase61_weighted_decision.py` | — | MODIFIED | Updated dependency whitelist |
| `tests/unit/test_phase66_interactions.py` | 2750 | NEW | 181 tests across 82 sections |
| `docs/audits/phase66_dimension_interactions_report.md` | — | NEW | This report |

## Architecture

### Why Full Interaction Is Dangerous

With 4 dimensions, full pairwise modeling produces 6 pairs. Each pair can have
multiple direction combinations (3x3 = 9). That's 54 potential interaction terms,
each with its own factor. Compounding all 54 produces chaotic, unexplainable
behavior. Learned interaction strengths compound the problem by introducing
feedback loops between dimensions.

### Why Sparse Pairwise Works

Phase 66 limits interactions to:
- **Static rules**: direction-based conditions, not learned
- **Bounded factors**: [0.9, 1.1] per rule, [0.9, 1.1] after product
- **Sparse selection**: max 3 active pairs from all matched rules
- **Strength-weighted**: weak signals produce attenuated factors

This gives the system enough interaction awareness to capture the most important
cross-dimension effects without instability.

### Default Interaction Rules

| Pair | Condition | Factor | Label |
|------|-----------|--------|-------|
| TREND + RISK | trend positive, risk negative | 0.95 | Caution: uptrend with high risk |
| TREND + RISK | trend positive, risk positive | 1.05 | Boost: uptrend with low risk |
| STABILITY + URGENCY | stability negative, urgency negative | 0.90 | Danger: unstable + urgent |
| STABILITY + URGENCY | stability positive, urgency negative | 1.05 | Confident: stable + urgent |

### Strength Weighting

Raw factors are attenuated by signal strength:
```
weighted_factor = 1.0 + (rule_factor - 1.0) * min(strength_a, strength_b)
```

Weak signals (low strength) produce factors close to neutral. Only strong,
confident signals trigger the full interaction effect.

### Selection Algorithm

1. Evaluate all rules against current dimension regimes
2. Filter: direction must match, combined strength >= threshold
3. Discard neutral factors (deviation < 0.0001)
4. Sort by |factor - 1.0| descending (most impactful first)
5. Take top N = max_active_pairs
6. Compute product, clamp to [0.9, 1.1]

### Pipeline Integration

```
final_score = base_score × regime_factor × feedback_factor × weight_factor × interaction_factor
```

Interaction is the final stage, applied uniformly to all candidates. It describes
the environment (dimension interactions), not candidate-specific qualities.

## Invariants

| ID | Invariant | Mechanism |
|----|-----------|-----------|
| 303 | Interaction bounded [0.9, 1.1] | Clamp on product and per-rule factor |
| 304 | Cannot override base ordering alone | ±10% max swing |
| 305 | Sparse: max 3 active pairs | Selection truncation |
| 306 | Deterministic | Pure computation, no randomness |
| 307 | No circular dependency | Only imports regime_aggregation types |
| 308 | Missing inputs → neutral (1.0) | None/empty → 1.0 fallback |
| 309 | Explainable | Active pairs, labels, factors in explanation |
| 310 | No combinatorial explosion | Bounded rules + sparse selection |
| 311 | No mutation of signals | Frozen dataclasses, no input modification |
| 312 | Disable = no effect | enabled=False → neutral, 0 evaluations |

## Backward Compatibility

- `InteractionConfig.enabled` defaults to `False` — no behavior change unless opted in
- `interaction_factor=1.0` default in StrategyCandidate is multiplicative identity
- All existing `orchestrate_selection` calls continue to work with no interaction effect
- All Phase 58 tests pass (167/167) with to_dict/whitelist updates
- All Phase 61 tests pass (153/153) with whitelist update

## Known Limitations

- Static interaction rules — no learned interaction strength
- No temporal interaction modeling — rules don't change over time
- No higher-order (triplet) interactions — only pairwise
- Direction-based matching only — no continuous direction input
- Uniform interaction factor across all candidates in a batch

## Test Coverage

181 tests across 82 sections covering:
- Config defaults, bounds, frozen, to_dict
- InteractionRule factor clamping, to_dict
- InteractionDirection enum values
- Direction matching logic
- Rule evaluation (matching, non-matching, missing dimensions, below threshold)
- Strength weighting (full, partial, minimum)
- ActiveInteraction deviation, to_dict, clamping
- InteractionResult defaults, bounds, frozen, to_dict
- Disabled behavior (neutral, no evaluation)
- No regimes → neutral
- Trend+risk interactions (caution, boost, no trend)
- Stability+urgency interactions (danger, confident)
- Selection top-N, sorted by deviation
- Clamping [0.9, 1.1] (low product, high product, within bounds)
- Safety (cannot dominate, max swing, base ordering preserved)
- Determinism (100-run consistency)
- Explainability (populated, matched/active counts, labels)
- No mutation (regimes unchanged, config unchanged)
- Custom rules, no matching rules, empty defaults
- Partial regimes, single dimension, all four dimensions
- All direction combinations bounded (81 combos)
- Neutral factors filtered out
- Multiple same-pair rules
- Strength monotonicity
- Orchestrator integration (candidate, result, disabled, enabled, to_dict)
- Pipeline isolation, compound stages
- Regression against Phase 58, Phase 61

## Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 30-66 | 4834 | PASS |

## Composition Stack

```
Phase 58: strategy_orchestrator  — base → regime → feedback → weight
Phase 66: dimension_interactions — + interaction_factor (final stage)
```

Interaction is the outermost modulation layer. It operates on the environment
state (dimension regimes), not on individual candidate properties.
