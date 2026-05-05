# Phase 73: Pattern-Specific Half-Life — Audit Report

**Date:** 2026-05-02
**Status:** COMPLETE
**Invariants:** 373–382 (10 total, all verified)

---

## Prerequisite Fix: Phase 61/69 Import Whitelist Drift

Phase 69 added `pattern_aggregation`, `pattern_influence`, and
`pattern_matching` imports to `strategy_orchestrator.py`, but the Phase 61
whitelist test (`test_orchestrator_imports_include_weighted_decision`) was
never updated. Patched the `allowed` set to include the three new modules.
Phase 61 regression: 153 passed, 0 failures.

---

## What Phase 73 Does

Refines the global/regime half-life on a per-pattern basis using each
pattern's historical reliability. Reliable patterns (consistent outcomes)
get longer memory; noisy patterns (high outcome variance) decay faster.
Patterns with insufficient samples fall back to the global half-life.

### Formulas

- **noise** = clamp(variance / 0.25, 0, 1)
- **reliability** = 1 - noise
- **multiplier selection**:
  - reliability >= reliability_threshold → reliable_multiplier (default 1.5)
  - noise >= noise_threshold → noisy_multiplier (default 0.6)
  - else → base_multiplier (default 1.0)
- **pattern_half_life** = clamp(base_half_life × multiplier, min_half_life, max_half_life)

### Priority Chain (unchanged)

1. `config.half_life` (base)
2. `adaptive_result` (Phase 71 — volatility adjustment)
3. `regime_result` (Phase 72 — regime adjustment)
4. `pattern_half_life_results` (Phase 73 — per-pattern refinement) ← **new**

---

## Files Created

| File | Purpose |
|------|---------|
| `umh/runtime/pattern_half_life.py` | Config, result, noise/reliability/half-life computation |
| `tests/unit/test_phase73_pattern_half_life.py` | 118 tests across 28 classes |

## Files Modified

| File | Change |
|------|--------|
| `umh/runtime/pattern_temporal.py` | Accept `pattern_half_life_results`, per-pattern decay, `pattern_applied` field |
| `umh/runtime/__init__.py` | Export 6 new symbols |
| `tests/unit/test_phase61_weighted_decision.py` | Import whitelist patch (3 modules added) |

---

## Invariants 373–382

| # | Statement | Verified |
|---|-----------|----------|
| 373 | Pattern-specific half-life is off by default | YES |
| 374 | Low-sample patterns fall back to global half-life | YES |
| 375 | Reliable patterns get longer memory (higher multiplier) | YES |
| 376 | Noisy patterns get shorter memory (lower multiplier) | YES |
| 377 | No mutation of pattern records | YES (frozen dataclass) |
| 378 | Deterministic — same inputs produce same outputs | YES |
| 379 | Missing stats produce neutral fallback | YES |
| 380 | Explainable — result carries explanation string | YES |
| 381 | No scoring feedback loop — uses variance not mean | YES |
| 382 | Clamped to [min_half_life, max_half_life] | YES |

---

## Test Results

| Suite | Passed | Failed |
|-------|--------|--------|
| Phase 73 unit tests | 118 | 0 |
| Phase 60-66 regression | 1,043 | 0 |
| Phase 67-73 regression | 801 | 0 |
| Phase 30-59 regression | 3,838 | 0 |
| **Total** | **5,800** | **0** |

---

## Known Limitations

1. **Static scores only** — pattern scores are provided as a flat list; no
   windowed or time-weighted variance computation.
2. **Single variance metric** — noise uses population variance / 0.25;
   alternative measures (MAD, IQR) are not supported.
3. **No cross-pattern influence** — each pattern's half-life is independent;
   correlated patterns are not grouped.

---

## Phase 74 Readiness

Phase 73 adds no breaking changes. The `pattern_half_life_results` parameter
in `apply_temporal_weights` is optional and defaults to `None`. All prior
callers continue to work unchanged. The module is safe for downstream
integration.

**Phase 74 is safe to proceed.**
