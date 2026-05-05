# Phase 61 — Weighted Decision Influence Layer v1

## Status: COMPLETE

## Summary

Phase 61 introduces bounded, confidence-gated influence of learned dimension weights
on the strategy selection pipeline. Weights now actively bias scoring — the first time
learned structure from Phase 60 affects decisions rather than just attaching metadata.

The design is deliberately conservative: disabled by default, max 10% influence,
confidence-gated at 0.60, and uniform across all candidates (preserving rank order
for all but the closest races).

## Files

| File | Action | Purpose |
|------|--------|---------|
| `umh/runtime/weighted_decision.py` | NEW | Core computation: weight factor, batch application |
| `umh/runtime/strategy_orchestrator.py` | MODIFIED | 4th pipeline stage, new fields on Candidate/Result |
| `umh/runtime/__init__.py` | MODIFIED | 6 new exports |
| `tests/unit/test_phase61_weighted_decision.py` | NEW | 153 tests across 60 sections |
| `tests/unit/test_phase58_strategy_orchestration.py` | MODIFIED | Updated allowed imports + dict key sets |
| `docs/audits/phase61_weighted_decision_report.md` | NEW | This report |

## Architecture

### Influence vs Authority

The fundamental design principle: **weights influence but never dominate**.

Base score remains the primary authority (inv 257). The weight factor is a multiplier
bounded to [1 - max_influence, 1 + max_influence], default [0.90, 1.10]. This means
a 10% maximum swing — enough to tip a close race, never enough to flip a dominant leader.

### Pipeline Order

```
base_score → regime_factor → feedback_factor → weight_factor
  (inv 233)    (Phase 46)     (Phase 57)        (Phase 61)
```

Each stage multiplies the previous result. The weight factor is computed once from
the current regime context and dimension weights, then applied uniformly to all
candidates. This uniform application means rank order is always preserved — the
weight factor can only change selection when candidates are very close in score.

### Weight Factor Computation

```
For each dimension (trend, risk, stability, urgency):
    signal_strength = regime.strength × regime.confidence
    weighted_contribution = signal_strength × dimension_weight × direction_sign
    
raw_factor = Σ(weighted_contributions)
clamped = clamp(raw_factor, -1.0, 1.0)
weight_factor = 1.0 + clamped × max_weight_influence
```

`direction_sign`: POSITIVE → +1, NEGATIVE → -1, NEUTRAL → 0.

### Confidence Gate

If overall weight confidence (mean across all dimension weights) falls below
`min_confidence` (default 0.60), the weight factor degrades to 1.0 — no effect.
This prevents poorly-learned weights from influencing decisions (inv 259).

## Invariants

| # | Statement | Verification |
|---|-----------|-------------|
| 257 | Base score remains primary authority | Weight factor bounded [0.90, 1.10]; uniform across candidates; large gaps never flipped |
| 258 | Weight influence must be bounded | `max_weight_influence` clamped to [0.0, 0.50]; factor always within [1-max, 1+max] |
| 259 | Influence degrades to neutral with low confidence | Confidence gate: overall < min_confidence → factor = 1.0 |
| 260 | No dimension may dominate decision | Uniform factor applied to all candidates; dimension contributions weighted by learned vector |
| 261 | No circular feedback loop | weighted_decision.py imports only dimension_weighting + regime_aggregation; no scoring module imports |
| 262 | Deterministic behavior only | No random, no timestamps, no ordering variance; 100-run determinism test passes |
| 263 | Missing weights → neutral | None weights/regime → default/NEUTRAL_AGGREGATED → factor = 1.0 |
| 264 | Explainability required | Explanation includes raw, factor, confidence, per-dimension contributions |

## No Circular Dependencies

```
weighted_decision.py
  ├── imports from: dimension_weighting (weights)
  └── imports from: regime_aggregation (regime state)

strategy_orchestrator.py
  ├── TYPE_CHECKING import: weighted_decision (types only)
  └── runtime import: weighted_decision (only when policy.enabled)
```

weighted_decision.py never imports from strategy_orchestrator, feedback_selection,
or any scoring module. The orchestrator uses a lazy runtime import to avoid circular
dependency at module load time.

## Safety Properties

1. **Disabled by default**: `WeightedDecisionPolicy.enabled = False`
2. **Bounded influence**: `max_weight_influence` capped at 0.50, default 0.10
3. **Confidence-gated**: Low-confidence weights produce no effect
4. **Uniform factor**: Same multiplier for all candidates — no per-candidate bias
5. **Rank preservation**: Uniform multiplication preserves candidate ordering
6. **Invalid/unsafe unchanged**: Weight factor never selects invalid/unsafe candidates
7. **Backward compatible**: All prior tests pass without modification of logic

## Why Weights Must Be Bounded

Unbounded weight influence would allow learned biases to override human-designed
scoring heuristics. The system has limited outcome data (Phase 60 requires 20 samples
for full confidence). Unbounded learned factors could:
- Amplify noise from small sample sizes
- Create positive feedback loops where early luck reinforces itself
- Override domain-expert base scoring with statistical artifacts

The 10% default bound means weights can express "this context slightly favors X"
but never "ignore base quality, pick X regardless."

## Interaction with Regime + Feedback

| Layer | Scope | Default |
|-------|-------|---------|
| Regime (Phase 46) | Per-candidate factor [0.85, 1.15] | Enabled |
| Feedback (Phase 57) | Per-candidate factor [0.0, 2.0] | Disabled |
| Weight (Phase 61) | Uniform factor [0.90, 1.10] | Disabled |

Regime factors vary per candidate (each strategy has its own regime alignment).
Feedback factors vary per candidate (each strategy has its own performance history).
Weight factors are uniform (context importance is the same regardless of strategy).

All three compose multiplicatively in strict order.

## Known Limitations

1. **Still correlation-based**: weights learn from variance in bucket scores, not causal mechanisms
2. **No temporal adaptation**: weight factor doesn't account for regime change velocity
3. **No multi-step planning influence**: weight factor is memoryless — no strategic lookahead
4. **No contextual bandit**: doesn't explore alternative weighting to improve learning
5. **Uniform factor**: cannot express "strategy A benefits more from high trend weight than strategy B"
6. **No decay**: weight influence doesn't fade as regime context ages

## Test Coverage

- 153 tests across 60 sections
- Coverage areas: policy defaults/bounds/dict/frozen, result defaults/bounds/dict/frozen,
  batch defaults/dict, direction_sign, overall_confidence, raw_weight_factor,
  normalize_to_bounded_factor, compute_weight_factor (disabled/missing/confidence/bounded/positive/negative),
  apply_weighted_influence (empty/disabled/boost/penalty/uniform/confidence/padding),
  determinism (100-run), explainability, StrategyCandidate weight_factor field,
  StrategySelectionResult new fields, orchestrator integration (default/neutral/boost/preserved/order/gate/invalid/composition/explanation/dict),
  dependency checks, no mutation, Phase 60/59/58 regression, init exports,
  edge cases (single/tie/stress), no execution methods, roundtrips, full pipeline,
  no-flip large gap, tip close race, weight magnitude, zero influence, empty selection, no randomness

## Phase 62 Safety

Phase 62 is safe to proceed. Potential directions:
- Per-candidate weight modulation (strategy-specific dimension affinity)
- Temporal weight decay (diminishing influence as regime ages)
- Weight influence on exploration policy (bias explore vs exploit)
- Causal dimension weighting (move beyond variance-based importance)
