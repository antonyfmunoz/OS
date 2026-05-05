# Phase 68 — Pattern Influence Layer v1

## Summary

Pattern influence enables bounded scoring adjustments based on historical
pattern performance from Phase 67's memory. Influence is **off by default**
and requires explicit enablement plus 4 independent quality gates.

## Files

| File | Action |
|------|--------|
| `umh/runtime/pattern_influence.py` | NEW — core module |
| `umh/runtime/strategy_orchestrator.py` | MODIFIED — 6th scoring factor |
| `umh/runtime/__init__.py` | MODIFIED — exports |
| `tests/unit/test_phase68_pattern_influence.py` | NEW — 55 tests |
| `docs/audits/phase68_pattern_influence_report.md` | NEW — this report |

## Scoring Composition

```
final_score = base × regime × feedback × weight × interaction × pattern
```

Pattern is applied LAST in the pipeline (Step 6).

## Gating (4 independent checks)

All must pass or factor = 1.0 (neutral):

1. `enabled == True` (default: False)
2. `sample_size >= min_samples` (default: 10)
3. `confidence >= min_confidence` (default: 0.6)
4. `similarity >= similarity_threshold` (default: 0.75)

## Signal Computation

```
pattern_signal = pattern_avg_score - candidate_score
clamped = clamp(signal, -max_adjustment, +max_adjustment)
factor = 1.0 + clamped
factor = clamp(factor, 0.9, 1.1)
```

## Why Gating Exists

Without gating, low-quality pattern data (few samples, low similarity)
would create noise in scoring. The 4 gates form a statistical quality
barrier — only strong evidence with sufficient data can influence scores.

## Why Confidence Matters

Confidence scales with sample size. A pattern seen 3 times has low
confidence; one seen 50 times has high confidence. This prevents
premature pattern-based adjustments from sparse observations.

## Why Influence is Capped

The hard clamp [0.9, 1.1] means pattern influence can never adjust
a score by more than ±10%. This prevents patterns from dominating
the base scoring signal or flipping clearly superior candidates.

## How This Avoids Feedback Loops

Pattern influence is **read-only** from memory (inv 330, 331).
It reads PatternResult from Phase 67 but never writes back to
PatternMemory. Patterns are recorded by the observation layer
(Phase 67), not by the influence layer (Phase 68).

## How This Differs from Learning

Learning adapts parameters over time. Pattern influence is a
fixed, stateless computation — given the same input, it always
produces the same output. No state is accumulated or modified.

## Invariants Verified

| # | Invariant | Status |
|---|-----------|--------|
| 323 | Pattern influence bounded [0.9, 1.1] | VERIFIED |
| 324 | Requires min_samples | VERIFIED |
| 325 | Requires min_confidence | VERIFIED |
| 326 | Requires similarity threshold | VERIFIED |
| 327 | Cannot override clear superior candidate | VERIFIED |
| 328 | Deterministic | VERIFIED |
| 329 | Missing pattern → neutral | VERIFIED |
| 330 | No mutation of memory | VERIFIED |
| 331 | No feedback loop (read-only memory) | VERIFIED |
| 332 | Explainable influence | VERIFIED |
| 333 | No dominance over base score | VERIFIED |

## Known Limitations

- No temporal weighting (old vs recent patterns weighted equally)
- No decay of old patterns
- No multi-pattern blending (uses best match only)
- No causal attribution (correlation, not causation)
- No per-strategy pattern mapping (same factor for all candidates)

## Test Coverage

55 tests across 13 test classes:
- Gating: 8 tests (disabled, low samples, low confidence, low similarity)
- Basic influence: 4 tests
- Bounds: 6 tests
- Safety: 3 tests
- Neutral/missing: 5 tests
- Determinism: 1 test (50 repetitions)
- Isolation: 2 tests
- Config: 4 tests
- Explainability: 2 tests
- StrategyCandidate: 5 tests
- Orchestrator integration: 8 tests
- Edge cases: 4 tests
- End-to-end with real memory: 3 tests
